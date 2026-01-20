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
# 直观理解 labels:类似 Excel的表头
# 这里演示的是手动埋点的方法
# ============================================
'''
更简单的方法:
# 方式1：用 prometheus-fastapi-instrumentators（推荐）
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# 一行启用监控，自动统计请求数、耗时等
Instrumentator(
    group_name="app_a"  # ← 加上分组名，会变成app_a_http_requests_total,这样这些指标就不会重复了
).instrument(app).expose(app, "/metrics")

# 方式2：用 starlette-exporter,功能上与本代码等价
from starlette_exporter import PrometheusMiddleware, PrometheusGaugeMiddleware

app.add_middleware(PrometheusMiddleware)
app.add_middleware(PrometheusGaugeMiddleware)
'''

# counter指标，统计事件发生的次数
def get_or_create_counter(name, description, labels):
    """
    获取或创建 Counter 指标（防重复注册）

    功能：
        从 Prometheus 注册表中查找指定名称的 Counter 指标，如果存在则返回，不存在则创建一个新的 Counter 并注册到注册表中。

    输入参数：
        name (str): 指标的名称，必须唯一，例如 'http_requests_total'
        description (str): 指标的描述信息，用于人类阅读，例如 'HTTP 请求总数'
        labels (list): 指标的标签列表，用于分组统计，例如 ['method', 'path', 'status']

    输出：
        Counter: 返回 Prometheus Counter 对象实例

    示例：
        counter = get_or_create_counter('my_counter', '请求计数', ['method', 'status'])
        counter.labels(method='GET', status='200').inc()  # 增加计数
    """
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Counter(name, description, labels)

# 直方图，统计数据的分布，适合请求分布耗时
def get_or_create_histogram(name, description, labels, buckets):
    """
    获取或创建 Histogram 指标（防重复注册）

    功能：
        从 Prometheus 注册表中查找指定名称的 Histogram 指标，如果存在则返回，
        不存在则创建一个新的 Histogram 并注册到注册表中。
        Histogram 用于统计数据的分布情况，自动计算分位数（如 p50、p95、p99）。

    输入参数：
        name (str): 指标的名称，必须唯一，例如 'http_request_duration_seconds'
        description (str): 指标的描述信息，例如 'HTTP 请求耗时（秒）'
        labels (list): 指标的标签列表，例如 ['method', 'path']
        buckets (tuple): 直方图的桶边界值（元组），决定分位数的计算粒度，
                        例如 (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)

    输出：
        Histogram: 返回 Prometheus Histogram 对象实例

    示例：
        histogram = get_or_create_histogram(
            'request_duration', '请求耗时', ['method'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
        )
        histogram.labels(method='GET').observe(0.05)  # 记录一个耗时 0.05 秒的请求
    """
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Histogram(name, description, labels, buckets=buckets)


# 表示当前状态:	可增可减的仪表盘，表示当前状态,比如看当亲啊并发请求数
def get_or_create_gauge(name, description):
    """
    获取或创建 Gauge 指标（防重复注册）

    功能：
        从 Prometheus 注册表中查找指定名称的 Gauge 指标，如果存在则返回，
        不存在则创建一个新的 Gauge 并注册到注册表中。
        Gauge 表示一个可以随时增加或减少的数值，适合表示当前状态或瞬时值。

    输入参数：
        name (str): 指标的名称，必须唯一，例如 'http_requests_in_progress'
        description (str): 指标的描述信息，例如 '当前正在处理的 HTTP 请求数'

    输出：
        Gauge: 返回 Prometheus Gauge 对象实例

    示例：
        gauge = get_or_create_gauge('active_connections', '当前活跃连接数')
        gauge.inc()   # 增加 1
        gauge.dec()   # 减少 1
        gauge.set(10) # 设置为指定值 10
    """
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Gauge(name, description)

# Counter：统计 HTTP 请求总数
http_requests_total = get_or_create_counter(
    'lmx_http_requests_total',
    'HTTP 请求总数',
    ['method', 'path', 'status']
)

# Histogram：统计 HTTP 请求响应时间
http_request_duration_seconds = get_or_create_histogram(
    'lmx_http_request_duration_seconds',
    'HTTP 请求耗时（秒）',
    ['method', 'path'],
    (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Gauge：当前正在处理的请求数
http_requests_in_progress = get_or_create_gauge(
    'lmx_http_requests_in_progress',
    '当前正在处理的 HTTP 请求数'
)


# ============================================
# Prometheus 中间件
# ============================================

@app.middleware("http") # 装饰器,声明这是一个http中间件,所有请求都会先经过他
async def prometheus_middleware(request: Request, call_next):
    """
    async:声明这是异步函数，不会阻塞其他请求.相当于声明:这个函数可能需要等待，耐心等，不要阻塞别人
    监控 HTTP 请求的中间件,每当请求进来的时候,会自动执行这套监控逻辑.
    """
    # 1. 增加并发请求计数,这个对应Gauge这个指标(当前正在处理的请求数)
    http_requests_in_progress.inc()

    # 2. 记录请求开始时间
    start_time = time.time()

    # 3. 提取请求信息,这个信息会成为我们label的一部分
    method = request.method
    path = request.url.path

    try:
        # 4. 调用下一个处理器(这里为啥是执行业务逻辑?有点不太懂)
        response = await call_next(request) # 这块才是真正的处理时间.这里会等待异步操作完成，再执行下一行代码
        # 这里要声明为异步函数主要也是因为这里,假如说这里业务逻辑要查询数据库,需要100ms,这时候这里100ms中间,服务器可以去处理其他的请求.
        status_code = response.status_code

        # 5. 计算请求耗时,请求耗时会成为我们指标的一部分
        duration = time.time() - start_time

        # 6. 记录指标,对应前面的:统计 HTTP 请求总数
        http_requests_total.labels(
            method=method,
            path=path,
            status=str(status_code)
        ).inc()

        # 对应前面的 统计 HTTP 请求响应时间 这个指标
        http_request_duration_seconds.labels(
            method=method,
            path=path
        ).observe(duration) # observe 记录这次请求耗时

        return response

    except Exception as e:
        # 异常处理：记录 5xx 错误
        # 如果请求处理时抛出异常（如代码报错），会走 except 分支.这时候同样记录耗时,记录请求数,然后raise抛出异常
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

# 暴露指标端点
@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus 指标暴露端点"""
    return generate_latest()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
