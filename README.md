# md-formula-docx-skill（中文教程）

将 Markdown 文档按参考模板转换为 DOCX，并把反引号中的数学表达式转换为 Word/WPS 可编辑公式（OMML）。

## 功能概览

- 输入：`md` 文件 + 参考模板 `docx`
- 输出：目标 `docx` + 可选 `report.json`
- 文本处理：普通文本不改写
- Markdown 结构：解析标题和列表
- 公式处理：仅对“被判定为数学表达式”的反引号内容调用 LLM
- 失败策略：单个公式失败时写入 `[公式转换失败]`，不中断整篇输出

## 技术架构

1. `md_parser.py`：解析标题、列表、段落、反引号片段
2. `formula_detector.py`：规则识别公式（非公式反引号保留原样）
3. `llm_latex.py`：将自然公式规范为 LaTeX（支持 `chat_completions` 与 `responses`）
4. `equation_renderer.py`：`LaTeX -> MathML -> OMML`
5. `style_mapper.py`：从模板提取和匹配段落/标题样式
6. `pipeline.py`：全流程编排、批量调用、容错、日志输出

## 环境要求

- Windows
- Python 3.10
- Microsoft Office（用于 `MML2OMML.XSL`）

默认 XSL 路径：
`C:\Program Files (x86)\Microsoft Office\Office14\MML2OMML.XSL`

安装依赖：

```powershell
py -3.10 -m pip install -r requirements.txt
```

## 配置

复制模板配置：

```powershell
Copy-Item .\config\model.example.yaml .\config\model.yaml
```

编辑 `config/model.yaml`。

### 方式 A：OpenAI Chat Completions

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key_env: "OPENAI_API_KEY"
  model: "gpt-4.1-mini"
  wire_api: "chat_completions"
  timeout: 30
  max_retries: 2
  batch_size: 12

equation:
  mml2omml_xsl: "C:\\Program Files (x86)\\Microsoft Office\\Office14\\MML2OMML.XSL"

output:
  failure_placeholder: "[公式转换失败]"
```

### 方式 B：OpenAI Responses（兼容网关）

```yaml
llm:
  base_url: "https://api.xxxaicode.com"
  api_key_env: "OPENAI_API_KEY"
  model: "gpt-5.4"
  wire_api: "responses"
  timeout: 45
  max_retries: 1
  batch_size: 16

equation:
  mml2omml_xsl: "C:\\Program Files (x86)\\Microsoft Office\\Office14\\MML2OMML.XSL"

output:
  failure_placeholder: "[公式转换失败]"
```

说明：
- `wire_api: responses` 会走 SSE 流式解析文本输出。
- `batch_size` 控制单次批量公式数量，适当调大可提速。

## 运行转换

推荐模块方式运行：

```powershell
py -3.10 -m scripts.pipeline `
  --input-md "D:\path\input.md" `
  --template-docx "D:\path\template.docx" `
  --output-docx "D:\path\out.docx" `
  --config "D:\path\model.yaml" `
  --log "D:\path\report.json"
```

参数：
- `--input-md`：输入 Markdown 文件
- `--template-docx`：参考 DOCX 模板
- `--output-docx`：输出 DOCX
- `--config`：YAML 配置（可选）
- `--log`：JSON 报告路径（可选）

## 报告说明（report.json）

关键字段：
- `total_formula_candidates`
- `formula_success`
- `formula_failed`
- `failures[]`：失败公式详情（表达式、行号、阶段、错误）

## 测试

```powershell
py -3.10 -m pytest -q
```

## 安全建议

- 不要把真实 API Key 提交到仓库。
- 仓库已忽略 `config/model.yaml`，建议只提交 `config/model.example.yaml`。

## 已知注意事项

- 某些网关在 `chat/completions` 可能返回空内容，需切换到 `wire_api: responses`。
- 如果出现编码问题，建议在运行前设置：
  `set PYTHONIOENCODING=utf-8`（或 PowerShell 中 `$env:PYTHONIOENCODING='utf-8'`）。