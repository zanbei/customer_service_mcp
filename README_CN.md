# 基于LangChain和MCP的电子商务客户服务系统

这是一个模块化的客户服务系统，使用LangChain和模型上下文协议（Model Context Protocol，MCP）来处理电子商务客户关于订单和物流的询问。

## 项目结构

```
customer_service_mcp/
├── agents/
│   ├── base_agent.py         # 具有通用功能的基础代理类
│   ├── intent_recognition_agent.py  # 用于确定客户意图的代理
│   ├── order_issue_agent.py  # 用于处理订单相关问题的代理
│   └── logistics_issue_agent.py  # 用于处理物流问题的代理
├── services/
│   ├── order_service.py      # 管理订单数据的服务
│   └── sop_service.py        # 管理SOP决策树的服务
├── config/
│   └── mcp_config.py         # MCP服务器配置
├── main.py                   # 应用程序主入口点
├── requirements.txt          # 项目依赖
├── server.py                 # MCP服务器实现
└── README.md                 # 项目文档
```

## 功能特性

- 多代理系统，用于处理客户询问
- 意图识别，将问题路由到适当的代理
- 具有持久存储的订单管理
- 带有决策树的标准操作程序（SOP）
- 对话历史跟踪
- MCP服务器集成，用于访问外部工具

## 设置

1. 创建并激活Python虚拟环境：
   ```bash
   # 创建虚拟环境
   python3 -m venv venv

   # 激活虚拟环境
   # 在Windows上：
   venv\Scripts\activate
   # 在Unix或MacOS上：
   source venv/bin/activate
   ```

2. 安装依赖：
   ```bash
   pip3 install -r requirements.txt
   ```

3. 配置AWS凭证以使用Bedrock：
   - 在`~/.aws/credentials`中设置AWS凭证，或使用环境变量
   - 确保您有权限访问AWS区域中的Bedrock服务

4. 运行交互式会话：
   ```bash
   python main.py
   ```

## MCP服务器使用

该系统使用FastMCP实现为MCP服务器，提供以下工具：

### 工具

1. `process_question`：处理客户服务询问
   - 输入：
     - question (str, 必需)：客户的问题
     - conversation_id (str, 可选)：用于维护对话上下文的ID
   - 输出：包含消息和对话ID的JSON响应

2. `get_order_info`：获取特定订单的信息
   - 输入：
     - order_id (str, 必需)：要查询的订单ID
   - 输出：包含订单详情或错误消息的JSON响应

3. `update_order_address`：更新订单的配送地址
   - 输入：
     - order_id (str, 必需)：要更新的订单ID
     - new_address (str, 必需)：新的配送地址
   - 输出：包含更新后的订单详情或错误消息的JSON响应

4. `get_sop_tree`：获取特定的SOP决策树
   - 输入：
     - sop_type (str, 必需)：SOP类型（"order"或"logistics"）
   - 输出：包含决策树内容或错误消息的JSON响应

### 运行服务器

#### 快速启动（Unix/Linux/MacOS）
只需运行提供的启动脚本：
```bash
./start_server.sh
```
该脚本将：
1. 如果不存在，创建Python虚拟环境
2. 激活虚拟环境
3. 如果需要，安装依赖
4. 启动MCP服务器

#### 手动设置（Windows或其他方式）
1. 创建并激活虚拟环境：
   ```bash
   # 创建虚拟环境
   python -m venv venv

   # 激活虚拟环境
   # 在Windows上：
   venv\Scripts\activate
   # 在Unix或MacOS上：
   source venv/bin/activate
   ```

2. 安装依赖：
   ```bash
   pip3 install -r requirements.txt
   ```

3. 启动MCP服务器：
   ```bash
   python server.py
   ```

服务器将以SSE（Server-Sent Events）传输模式启动，使其与各种MCP客户端兼容。启动后，服务器将暴露以下端点：
- 处理客户询问
- 获取订单信息
- 更新订单地址
- 访问SOP决策树

## 使用示例

```python
from main import CustomerServiceSystem

# 创建系统实例
system = CustomerServiceSystem()

# 处理问题
response, conv_id = system.process_question("订单#123的状态是什么？")
print(f"代理: {response}")
```

## 测试订单

系统预配置了以下测试订单：
- 订单#123：处理中
- 订单#456：已发货
- 订单#789：已送达

## 决策树

系统使用决策树来处理：
- 订单问题：状态查询、修改
- 物流问题：配送跟踪、地址变更、包裹丢失

## 贡献

1. Fork 仓库
2. 创建特性分支
3. 进行更改
4. 提交拉取请求

## 许可证

MIT 许可证
