# Jenkins Master 节点构建快速指南

## 📋 为什么选择 Master 节点？

**简化版（Master 节点）vs 复杂版（动态 Agent）对比：**

| 特性 | Master 节点 | 动态 Agent |
|------|------------|-----------|
| **配置难度** | ⭐ 超简单 | ⭐⭐⭐⭐ 复杂 |
| **理解成本** | 低，容易理解 | 高，需要理解 K8s Pod |
| **Docker 环境** | 直接使用 Master 的 Docker | 需要 DinD 容器 |
| **适合场景** | 学习、小项目 | 生产环境、大规模 |

**我们选择 Master 节点！** 🎯

## 🚀 快速开始（3 步）

### Step 1: 在 Jenkins 中添加 ACR 凭据

这是**唯一需要配置**的地方！

1. 在 Jenkins 中点击 `Manage Jenkins`（管理 Jenkins）
2. 点击 `Manage Credentials`（管理凭据）
3. 点击 `(global)` → `Add Credentials`（添加凭据）

**配置两个凭据：**

#### 凭据 1：ACR 用户名
- **Kind**: Secret text
- **Secret**: `曦雨馨香lin`
- **ID**: `acr-username`
- **Description**: ACR 用户名

#### 凭据 2：ACR 密码
- **Kind**: Secret text  
- **Secret**: `你的阿里云ACR密码`
- **ID**: `acr-password`
- **Description**: ACR 密码

### Step 2: 创建 Pipeline 任务

1. 在 Jenkins 首页点击 `新建任务`（New Item）
2. 输入任务名称：`test-project-build`
3. 选择 `Pipeline`
4. 点击 `确定`

### Step 3: 配置 Pipeline

在 Pipeline 配置页面：

**方式 A：从 Git 仓库读取（推荐）**
- **Definition**: `Pipeline script from SCM`
- **SCM**: `Git`
- **Repository URL**: 你的仓库地址
- **Script Path**: `test_project/Jenkinsfile.master`

**方式 B：直接粘贴脚本**
- **Definition**: `Pipeline script`
- 复制 `Jenkinsfile.master` 的内容粘贴进去

保存后，点击 `立即构建`！

## 📝 文件说明

现在你有 **3 个版本** 的 Jenkinsfile：

| 文件 | 运行位置 | 复杂度 | 推荐场景 |
|------|---------|-------|---------|
| `Jenkinsfile.master` | Jenkins Master | ⭐ 简单 | **初学者首选** ✅ |
| `Jenkinsfile.simple` | K8s Agent Pod | ⭐⭐⭐ 中等 | 有 K8s 基础 |
| `Jenkinsfile` | K8s Agent Pod | ⭐⭐⭐⭐ 复杂 | 生产环境 |

**建议：先用 `Jenkinsfile.master` 学习！**

## 🔧 前置准备

### 1. 确保 Jenkins Master 可以访问 Docker

Jenkins Master 必须能运行 Docker 命令。有两种方式：

**方式 A：Jenkins 容器挂载 Docker Socket（推荐）**

修改 Jenkins Deployment，添加 Docker Socket 挂载：

```yaml
# 在 04-deployment.yaml 中添加
volumeMounts:
- name: docker-sock
  mountPath: /var/run/docker.sock

volumes:
- name: docker-sock
  hostPath:
    path: /var/run/docker.sock
```

然后重新部署：
```bash
kubectl apply -f jenkins/04-deployment.yaml
```

**方式 B：在 Jenkins 容器中安装 Docker（不推荐，复杂）**

需要自定义 Jenkins 镜像，比较麻烦。

### 2. 检查 Docker 是否可用

进入 Jenkins Pod 测试：
```bash
kubectl exec -it -n jenkins deployment/jenkins -- docker --version
```

如果看到 Docker 版本信息，说明配置成功！

## 📊 构建流程说明

```
1. 代码检出 
   └─ 从 Git 拉取代码

2. 环境检查
   └─ 检查 Docker 是否可用

3. 构建镜像
   └─ 在 test_project 目录执行 docker build
   └─ 打上 3 个标签：构建号、Git SHA、latest

4. 镜像测试
   └─ 启动临时容器验证
   └─ 测试通过后清理

5. 推送到 ACR
   └─ 使用 Jenkins 凭据登录 ACR
   └─ 推送 3 个标签的镜像
```

**整个过程大约 3-5 分钟！**

## ⚠️ 常见问题

### Q1: 提示 "docker: command not found"

**原因**：Jenkins Master 访问不到 Docker

**解决**：
1. 按照上面"前置准备"挂载 Docker Socket
2. 重启 Jenkins Pod：`kubectl rollout restart deployment/jenkins -n jenkins`

### Q2: 推送镜像时提示 "unauthorized"

**原因**：ACR 凭据配置错误

**解决**：
1. 检查 Jenkins 凭据中的用户名和密码是否正确
2. ID 必须是 `acr-username` 和 `acr-password`

### Q3: 找不到 test_project 目录

**原因**：Git 仓库配置错误或路径不对

**解决**：
1. 确认 Git 仓库 URL 正确
2. 确认仓库根目录下有 `test_project` 文件夹

### Q4: 构建很慢

**原因**：首次构建需要拉取基础镜像

**正常现象**！第一次构建可能需要 5-10 分钟，后续会快很多（有缓存）。

## 🎯 验证成功

构建成功后，你应该能看到：

1. ✅ Jenkins 日志显示 "构建成功"
2. ✅ 在阿里云 ACR 控制台看到新的镜像版本
3. ✅ 镜像有 3 个标签：构建号、Git SHA、latest

## 🎓 关键点理解（初学者视角）

### 什么是 Master 节点？

- **Master 节点** = Jenkins 自己运行的那个容器
- 就像你在自己电脑上运行命令一样简单
- 不需要额外创建其他容器

### Agent 和 Master 的区别？

**Master 节点方式：**
```
Jenkins 容器 → 直接运行 docker build → 完成
```

**Agent 方式：**
```
Jenkins 容器 → 创建新的 Agent Pod → Agent 运行 docker build → 完成 → 删除 Agent
```

看出来了吧？Master 方式简单得多！

### 为什么需要 Docker Socket？

- Jenkins 容器本身不包含 Docker
- 挂载 `/var/run/docker.sock` 让 Jenkins 可以使用宿主机的 Docker
- 就像"借用"宿主机的 Docker 环境

## 🚀 下一步

学会了 Master 节点构建后，你可以：

1. **尝试修改代码** → 推送 → 看 Jenkins 自动构建
2. **配置 Webhook** → 实现代码推送自动触发
3. **了解 Agent 方式** → 等熟练后再尝试

## 📚 参考文档

- Jenkins Pipeline 语法：https://www.jenkins.io/doc/book/pipeline/syntax/
- Docker 命令参考：https://docs.docker.com/engine/reference/commandline/cli/

---

**记住：简单有效才是最好的！** 😊
# Jenkins Master 节点构建快速指南

## 📋 为什么选择 Master 节点？

**简化版（Master 节点）vs 复杂版（动态 Agent）对比：**

| 特性 | Master 节点 | 动态 Agent |
|------|------------|-----------|
| **配置难度** | ⭐ 超简单 | ⭐⭐⭐⭐ 复杂 |
| **理解成本** | 低，容易理解 | 高，需要理解 K8s Pod |
| **Docker 环境** | 直接使用 Master 的 Docker | 需要 DinD 容器 |
| **适合场景** | 学习、小项目 | 生产环境、大规模 |

**我们选择 Master 节点！** 🎯

## 🚀 快速开始（3 步）

### Step 1: 在 Jenkins 中添加 ACR 凭据

这是**唯一需要配置**的地方！

1. 在 Jenkins 中点击 `Manage Jenkins`（管理 Jenkins）
2. 点击 `Manage Credentials`（管理凭据）
3. 点击 `(global)` → `Add Credentials`（添加凭据）

**配置两个凭据：**

#### 凭据 1：ACR 用户名
- **Kind**: Secret text
- **Secret**: `曦雨馨香lin`
- **ID**: `acr-username`
- **Description**: ACR 用户名

#### 凭据 2：ACR 密码
- **Kind**: Secret text  
- **Secret**: `你的阿里云ACR密码`
- **ID**: `acr-password`
- **Description**: ACR 密码

### Step 2: 创建 Pipeline 任务

1. 在 Jenkins 首页点击 `新建任务`（New Item）
2. 输入任务名称：`test-project-build`
3. 选择 `Pipeline`
4. 点击 `确定`

### Step 3: 配置 Pipeline

在 Pipeline 配置页面：

**方式 A：从 Git 仓库读取（推荐）**
- **Definition**: `Pipeline script from SCM`
- **SCM**: `Git`
- **Repository URL**: 你的仓库地址
- **Script Path**: `test_project/Jenkinsfile.master`

**方式 B：直接粘贴脚本**
- **Definition**: `Pipeline script`
- 复制 `Jenkinsfile.master` 的内容粘贴进去

保存后，点击 `立即构建`！

## 📝 文件说明

现在你有 **3 个版本** 的 Jenkinsfile：

| 文件 | 运行位置 | 复杂度 | 推荐场景 |
|------|---------|-------|---------|
| `Jenkinsfile.master` | Jenkins Master | ⭐ 简单 | **初学者首选** ✅ |
| `Jenkinsfile.simple` | K8s Agent Pod | ⭐⭐⭐ 中等 | 有 K8s 基础 |
| `Jenkinsfile` | K8s Agent Pod | ⭐⭐⭐⭐ 复杂 | 生产环境 |

**建议：先用 `Jenkinsfile.master` 学习！**

## 🔧 前置准备

### 1. 确保 Jenkins Master 可以访问 Docker

Jenkins Master 必须能运行 Docker 命令。有两种方式：

**方式 A：Jenkins 容器挂载 Docker Socket（推荐）**

修改 Jenkins Deployment，添加 Docker Socket 挂载：

```yaml
# 在 04-deployment.yaml 中添加
volumeMounts:
- name: docker-sock
  mountPath: /var/run/docker.sock

volumes:
- name: docker-sock
  hostPath:
    path: /var/run/docker.sock
```

然后重新部署：
```bash
kubectl apply -f jenkins/04-deployment.yaml
```

**方式 B：在 Jenkins 容器中安装 Docker（不推荐，复杂）**

需要自定义 Jenkins 镜像，比较麻烦。

### 2. 检查 Docker 是否可用

进入 Jenkins Pod 测试：
```bash
kubectl exec -it -n jenkins deployment/jenkins -- docker --version
```

如果看到 Docker 版本信息，说明配置成功！

## 📊 构建流程说明

```
1. 代码检出 
   └─ 从 Git 拉取代码

2. 环境检查
   └─ 检查 Docker 是否可用

3. 构建镜像
   └─ 在 test_project 目录执行 docker build
   └─ 打上 3 个标签：构建号、Git SHA、latest

4. 镜像测试
   └─ 启动临时容器验证
   └─ 测试通过后清理

5. 推送到 ACR
   └─ 使用 Jenkins 凭据登录 ACR
   └─ 推送 3 个标签的镜像
```

**整个过程大约 3-5 分钟！**

## ⚠️ 常见问题

### Q1: 提示 "docker: command not found"

**原因**：Jenkins Master 访问不到 Docker

**解决**：
1. 按照上面"前置准备"挂载 Docker Socket
2. 重启 Jenkins Pod：`kubectl rollout restart deployment/jenkins -n jenkins`

### Q2: 推送镜像时提示 "unauthorized"

**原因**：ACR 凭据配置错误

**解决**：
1. 检查 Jenkins 凭据中的用户名和密码是否正确
2. ID 必须是 `acr-username` 和 `acr-password`

### Q3: 找不到 test_project 目录

**原因**：Git 仓库配置错误或路径不对

**解决**：
1. 确认 Git 仓库 URL 正确
2. 确认仓库根目录下有 `test_project` 文件夹

### Q4: 构建很慢

**原因**：首次构建需要拉取基础镜像

**正常现象**！第一次构建可能需要 5-10 分钟，后续会快很多（有缓存）。

## 🎯 验证成功

构建成功后，你应该能看到：

1. ✅ Jenkins 日志显示 "构建成功"
2. ✅ 在阿里云 ACR 控制台看到新的镜像版本
3. ✅ 镜像有 3 个标签：构建号、Git SHA、latest

## 🎓 关键点理解（初学者视角）

### 什么是 Master 节点？

- **Master 节点** = Jenkins 自己运行的那个容器
- 就像你在自己电脑上运行命令一样简单
- 不需要额外创建其他容器

### Agent 和 Master 的区别？

**Master 节点方式：**
```
Jenkins 容器 → 直接运行 docker build → 完成
```

**Agent 方式：**
```
Jenkins 容器 → 创建新的 Agent Pod → Agent 运行 docker build → 完成 → 删除 Agent
```

看出来了吧？Master 方式简单得多！

### 为什么需要 Docker Socket？

- Jenkins 容器本身不包含 Docker
- 挂载 `/var/run/docker.sock` 让 Jenkins 可以使用宿主机的 Docker
- 就像"借用"宿主机的 Docker 环境

## 🚀 下一步

学会了 Master 节点构建后，你可以：

1. **尝试修改代码** → 推送 → 看 Jenkins 自动构建
2. **配置 Webhook** → 实现代码推送自动触发
3. **了解 Agent 方式** → 等熟练后再尝试

## 📚 参考文档

- Jenkins Pipeline 语法：https://www.jenkins.io/doc/book/pipeline/syntax/
- Docker 命令参考：https://docs.docker.com/engine/reference/commandline/cli/

---

**记住：简单有效才是最好的！** 😊
