"""
Test Project - FastAPI + Prometheus Metrics
"""
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest
import time

app = FastAPI(title="Test Project", version="1.0.0")

# ============================================
# Prometheus 指标定义（防重复注册）
# ============================================

def get_or_create_counter(name, description, labels):
    """获取或创建 Counter 指标"""
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Counter(name, description, labels)

def get_or_create_histogram(name, description, labels, buckets):
    """获取或创建 Histogram 指标"""
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Histogram(name, description, labels, buckets=buckets)

def get_or_create_gauge(name, description):
    """获取或创建 Gauge 指标"""
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Gauge(name, description)

# Counter：统计 HTTP 请求总数
http_requests_total = get_or_create_counter(
    'http_requests_total',
    'HTTP 请求总数',
    ['method', 'path', 'status']
)

# Histogram：统计 HTTP 请求响应时间
http_request_duration_seconds = get_or_create_histogram(
    'http_request_duration_seconds',
    'HTTP 请求耗时（秒）',
    ['method', 'path'],
    (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Gauge：当前正在处理的请求数
http_requests_in_progress = get_or_create_gauge(
    'http_requests_in_progress',
    '当前正在处理的 HTTP 请求数'
)


# ============================================
# Prometheus 中间件
# ============================================

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """监控 HTTP 请求的中间件"""
    # 1. 增加并发请求计数
    http_requests_in_progress.inc()

    # 2. 记录请求开始时间
    start_time = time.time()

    # 3. 提取请求信息
    method = request.method
    path = request.url.path

    try:
        # 4. 调用下一个处理器
        response = await call_next(request)
        status_code = response.status_code

        # 5. 计算请求耗时
        duration = time.time() - start_time

        # 6. 记录指标
        http_requests_total.labels(
            method=method,
            path=path,
            status=str(status_code)
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            path=path
        ).observe(duration)

        return response

    except Exception as e:
        # 异常处理：记录 5xx 错误
        duration = time.time() - start_time
        http_requests_total.labels(
            method=method,
            path=path,
            status="500"
        ).inc()
        http_request_duration_seconds.labels(
            method=method,
            path=path
        ).observe(duration)
        raise

    finally:
        # 减少并发计数
        http_requests_in_progress.dec()


# ============================================
# 路由
# ============================================

@app.get('/')
def hello():
    return {"message": "Hello DevOps! 我更新了！", "framework": "FastAPI"}


@app.get("/health")
def health():
    """健康检查接口"""
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus 指标暴露端点"""
    return generate_latest()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
