# PPX 项目 AI 编程规则

本文档为使用 AI 为 PPX 项目编写代码时需要遵循的规则和指南。

## 1. 项目概述

PPX 是一个使用 Python (`pywebview`) 作为后端，并允许任何前端框架（如 Vue.js, React, HTML）作为视图层的跨平台桌面应用框架。

- **后端**: Python, 核心是 `pywebview`。
- **前端**: JavaScript/TypeScript, 默认使用 Vue.js。
- **通信**: 通过 `pywebview` 的 `js_api` 和 `evaluate_js` 实现前后端双向通信。
- **打包**: 使用 `PyInstaller` 进行打包，通过 `package.json` 中的脚本执行。

## 2. 核心文件结构

- `main.py`: 应用主入口，负责创建窗口和注入 API。
- `api/`: 后端 API 目录。
  - `api/api.py`: API 主类，聚合其他 API 模块。
  - `api/system.py`: 系统相关 API（如文件操作）。
  - `api/storage.py`: 数据库相关 API。
- `pyapp/`: Python 后端应用的核心逻辑。
  - `pyapp/config/config.py`: 项目的核心配置文件。
  - `pyapp/db/`: 数据库模块。
- `gui/`: 前端代码目录 (Vue.js)。
  - `gui/src/App.vue`: 前端主组件。
  - `gui/src/components/`: 前端组件。
- `package.json`: 项目脚本和依赖管理。

## 3. 开发流程

### 3.1. 添加新的后端 API (JavaScript 调用 Python)

1.  **创建或选择 API 模块**: 根据功能，在 `api/` 目录下选择一个现有的模块（如 `system.py`）或创建一个新的 `.py` 文件。
2.  **定义方法**: 在选择的模块中，创建一个新的类，并定义公开方法。方法可以返回 JSON 兼容的数据类型 (dict, list, str, int, bool)。
    ```python
    # api/my_new_api.py
    class MyNewAPI:
        def do_something(self, params):
            # ... some logic ...
            return {"status": "success", "data": params}
    ```
3.  **聚合 API**: 在 `api/api.py` 中，导入并继承新的 API 类。
    ```python
    # api/api.py
    from api.storage import Storage
    from api.system import System
    from api.my_new_api import MyNewAPI # 导入新类

    class API(System, Storage, MyNewAPI): # 继承新类
        '''业务层API，供前端JS调用'''
        def setWindow(self, window):
            '''获取窗口实例'''
            System._window = window
    ```
4.  **前端调用**: 在前端 Vue 组件中，使用 `window.pywebview.api.method_name(params)` 进行调用。这是一个 `Promise`。
    ```javascript
    // gui/src/components/MyComponent.vue
    async function callPythonApi() {
      try {
        const params = { id: 1 };
        const result = await window.pywebview.api.do_something(params);
        console.log(result); // { status: 'success', data: { id: 1 } }
      } catch (e) {
        console.error(e);
      }
    }
    ```

### 3.2. 从后端调用前端函数 (Python 调用 JavaScript)

1.  **前端注册函数**: 在前端代码中，将一个函数挂载到 `window` 对象上。
    ```javascript
    // gui/src/main.js or a specific component
    window.updateProgress = (progress) => {
      console.log(`Current progress: ${progress}%`);
      // Update UI, e.g., store.commit('setProgress', progress)
    };
    ```
2.  **后端调用**: 在 Python API 方法中，使用 `self._window.evaluate_js()` 来执行前端函数。
    ```python
    # api/system.py
    import json

    class System:
        _window = None

        def start_long_task(self):
            # ... task started ...
            progress = 50
            self._window.evaluate_js(f"window.updateProgress({progress})")
            # ... task finished ...
            self._window.evaluate_js("window.updateProgress(100)")
    ```
    **注意**: 传递复杂对象时，需要先用 `json.dumps()` 序列化。

## 4. 状态管理

- **后端**: Python 侧是无状态的，每个 API 调用都是独立的。持久化数据应存入数据库。
- **前端**: 可以使用 Pinia 或其他 Vue 状态管理库来管理前端状态。

## 5. 数据库操作

- 项目支持 `TinyDB` (json) 和 `SQLite` (sql)。
- 数据库类型在 `pyapp/config/config.py` 的 `typeDB` 变量中配置。
- 所有数据库操作都应通过 `api/storage.py` 中定义的 API 进行，以确保一致性。

## 6. 打包和构建

- **开发**: 运行 `pnpm run start`。
- **生产打包**: 运行 `pnpm run build`。
- AI 无需直接操作打包命令，但编写的代码必须兼容生产环境。这意味着：
  - 文件路径必须使用相对路径，并考虑打包后的文件结构 (`web/` 目录)。
  - 避免使用只在特定操作系统上存在的依赖。

## 7. 代码风格

- **Python**: 遵循 PEP 8 规范。使用 `black` 和 `flake8` 进行格式化和检查。
- **JavaScript/Vue**: 遵循项目现有的 `.eslintrc.cjs` 和 `.prettierrc.js` 配置。
- **命名**:
  - Python 方法名: `snake_case` (例如 `get_user_data`)。
  - JavaScript 函数名: `camelCase` (例如 `getUserData`)。