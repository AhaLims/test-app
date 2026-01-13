# test_project CI/CD 配置说明

## Jenkinsfile 说明

本项目包含一个完整的 CI/CD Pipeline 配置文件 `Jenkinsfile`，用于自动化构建 Docker 镜像并推送到阿里云 ACR。

### Pipeline 流程

```
代码检出 → 环境准备 → 构建镜像 → 镜像测试 → 推送到 ACR → 部署到 K8s
```

### 镜像标签策略

每次构建会生成三个标签的镜像：
1. **构建号标签**: `linmoxin:123`（可追溯到具体构建）
2. **Git Commit 标签**: `linmoxin:abc1234`（可追溯到代码版本）
3. **Latest 标签**: `linmoxin:latest`（始终指向最新版本）

完整镜像地址示例：
```
crpi-ligqgn7j175l602u.cn-guangzhou.personal.cr.aliyuncs.com/linmoxin/linmoxin:123
crpi-ligqgn7j175l602u.cn-guangzhou.personal.cr.aliyuncs.com/linmoxin/linmoxin:abc1234
crpi-ligqgn7j175l602u.cn-guangzhou.personal.cr.aliyuncs.com/linmoxin/linmoxin:latest
```

## 在 Jenkins 中创建 Pipeline 任务

### 步骤 1：创建新任务

1. 登录 Jenkins UI
2. 点击 "新建任务"
3. 输入任务名称：`test-project-pipeline`
4. 选择 "Pipeline"
5. 点击 "确定"

### 步骤 2：配置任务

#### 通用配置

- **描述**: test_project 自动化构建和部署
- **参数化构建**: 启用（可选）
  - 字符串参数：`BRANCH` = `main`
  - 布尔参数：`PUSH_TO_ACR` = `true`
  - 布尔参数：`DEPLOY_TO_K8S` = `false`

#### Pipeline 配置

**定义**: Pipeline script from SCM

**SCM**: Git
- **Repository URL**: 你的 Git 仓库地址
- **Credentials**: 添加 Git 凭据（如需要）
- **Branch**: `*/main` 或 `*/${BRANCH}`

**Script Path**: `test_project/Jenkinsfile`

### 步骤 3：配置 ACR 凭据

由于 Jenkinsfile 使用了凭据管理，需要在 Jenkins 中添加 ACR 凭据。

#### 方法 1：使用 Jenkins Credentials（推荐）

1. 进入 `Manage Jenkins` → `Manage Credentials`
2. 选择 `Global` → `Add Credentials`
3. 配置第一个凭据（用户名）：
   - **Kind**: Secret text
   - **Secret**: `曦雨馨香lin`
   - **ID**: `acr-username`
   - **Description**: ACR 用户名
4. 配置第二个凭据（密码）：
   - **Kind**: Secret text
   - **Secret**: [你的 ACR 密码]
   - **ID**: `acr-password`
   - **Description**: ACR 密码

#### 方法 2：修改 Jenkinsfile 直接使用 K8s Secret

如果不想在 Jenkins 中配置凭据，可以修改 Jenkinsfile 的推送阶段：

```groovy
stage('Push to ACR') {
    steps {
        container('docker') {
            sh '''
                # 从 Kubernetes Secret 读取凭据
                ACR_USERNAME=$(cat /var/run/secrets/acr/username)
                ACR_PASSWORD=$(cat /var/run/secrets/acr/password)
                
                echo "登录阿里云 ACR..."
                echo $ACR_PASSWORD | docker login ${ACR_REGISTRY} -u $ACR_USERNAME --password-stdin
                
                echo "推送镜像..."
                docker push ${IMAGE_NAME}:${IMAGE_TAG}
                docker push ${IMAGE_NAME}:${GIT_COMMIT_SHORT}
                docker push ${IMAGE_NAME}:latest
            '''
        }
    }
}
```

然后在 Pod 模板中挂载 Secret：

```yaml
volumeMounts:
- name: acr-secret
  mountPath: /var/run/secrets/acr
  readOnly: true

volumes:
- name: acr-secret
  secret:
    secretName: acr-credentials
```

### 步骤 4：配置 Webhook（可选）

要实现代码推送自动触发构建，需要配置 Git Webhook。

#### GitHub Webhook 配置

1. 在 GitHub 仓库中进入 `Settings` → `Webhooks` → `Add webhook`
2. **Payload URL**: `http://<Jenkins地址>:30080/github-webhook/`
3. **Content type**: `application/json`
4. **Events**: 选择 `Just the push event`
5. 点击 `Add webhook`

#### Gitee/GitLab 配置

类似 GitHub，但 URL 可能需要调整为：
- Gitee: `http://<Jenkins地址>:30080/gitee-webhook/invoke`
- GitLab: `http://<Jenkins地址>:30080/project/test-project-pipeline`

### 步骤 5：首次手动构建

1. 进入 Pipeline 任务页面
2. 点击 "Build Now" 或 "Build with Parameters"
3. 观察构建日志
4. 验证镜像是否成功推送到 ACR

## 验证镜像推送

### 在阿里云控制台查看

1. 登录阿里云控制台
2. 进入容器镜像服务
3. 选择个人实例 → 命名空间 → `linmoxin/linmoxin`
4. 查看镜像版本列表

### 使用 Docker 命令验证

```bash
# 登录 ACR
docker login --username=曦雨馨香lin crpi-ligqgn7j175l602u.cn-guangzhou.personal.cr.aliyuncs.com

# 拉取镜像验证
docker pull crpi-ligqgn7j175l602u.cn-guangzhou.personal.cr.aliyuncs.com/linmoxin/linmoxin:latest

# 运行镜像测试
docker run -d -p 8080:80 crpi-ligqgn7j175l602u.cn-guangzhou.personal.cr.aliyuncs.com/linmoxin/linmoxin:latest

# 访问测试
curl http://localhost:8080
```

## 故障排查

### 问题 1: Docker 守护进程未启动

**现象**: 日志显示 "Cannot connect to the Docker daemon"

**解决方案**:
- 确认 Pod 模板中 docker 容器的 `securityContext.privileged` 设置为 `true`
- 增加 Docker 守护进程启动等待时间

### 问题 2: 凭据无法找到

**现象**: "Credentials not found: acr-username"

**解决方案**:
- 确认在 Jenkins 中已创建对应 ID 的凭据
- 或使用方法 2 直接从 K8s Secret 读取

### 问题 3: 推送镜像失败

**现象**: "unauthorized: authentication required"

**解决方案**:
- 验证 ACR 用户名和密码是否正确
- 检查网络连接到阿里云 ACR
- 确认镜像命名空间存在

### 问题 4: Git 仓库拉取失败

**现象**: "Failed to clone repository"

**解决方案**:
- 确认 Git 仓库地址正确
- 添加 Git 凭据（私有仓库）
- 检查网络连接

## 进阶配置

### 多分支构建

可以配置不同分支使用不同的镜像标签策略：

```groovy
environment {
    IMAGE_TAG = "${env.GIT_BRANCH == 'main' ? 'prod' : 'dev'}-${env.BUILD_NUMBER}"
}
```

### 构建通知

在 `post` 阶段添加邮件或钉钉通知：

```groovy
post {
    success {
        emailext(
            subject: "✅ 构建成功: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: "镜像已推送到 ACR: ${IMAGE_NAME}:${IMAGE_TAG}",
            to: "developer@example.com"
        )
    }
}
```

### 自动部署到 Kubernetes

启用 `DEPLOY_TO_K8S` 参数后，Pipeline 会自动更新 K8s Deployment：

```bash
kubectl set image deployment/test-app \
    test-app=${IMAGE_NAME}:${IMAGE_TAG} \
    -n default
```

需要确保 Jenkins ServiceAccount 有对应权限。

## 相关文档

- [Jenkins 配置目录](../jenkins/)
- [设计文档](../.qoder/quests/deploy-jenkins-with-acr-integration.md)
- [Kubernetes Plugin 文档](https://plugins.jenkins.io/kubernetes/)
