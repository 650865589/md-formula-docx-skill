# fomula_skill 使用教程（中文）

本项目用于把 Markdown 文档转换为 DOCX，并将反引号中的**数学表达式**转换为 Word/WPS 可编辑公式（OMML）。

核心原则：
- 普通文本不改写。
- 只解析 Markdown 的标题和列表结构。
- 只在“反引号内容被判定为数学表达式”时调用大模型。
- 公式失败不阻断整文档，写入占位符 `[公式转换失败]` 并记录日志。

## 1. 功能说明

输入：
- `md` 文件（包含正文、标题、列表、反引号内容）
- 参考样式 `docx` 模板（每次可传不同模板）

输出：
- 新 `docx` 文件（继承模板样式）
- 可选 `report.json`（转换统计和失败明细）

公式链路：
1. 反引号内容先经过脚本规则判定是否为公式。
2. 判定为公式才调用 LLM 转标准 LaTeX。
3. LaTeX 转 MathML，再通过 `MML2OMML.XSL` 转 OMML。
4. 插入到 DOCX 中，支持 Word/WPS 双击编辑。

## 2. 环境要求

- Windows（已验证）
- Python 3.10
- Microsoft Office（用于提供 `MML2OMML.XSL`，默认路径为 `C:\Program Files (x86)\Microsoft Office\Office14\MML2OMML.XSL`）

建议统一用以下命令，避免系统里多 Python 版本混用：

```powershell
py -3.10 -m pip install -r requirements.txt
```

## 3. 项目结构

```text
fomula_skill/
├─ config/
│  └─ model.example.yaml
├─ scripts/
│  ├─ pipeline.py
│  ├─ md_parser.py
│  ├─ formula_detector.py
│  ├─ llm_latex.py
│  ├─ equation_renderer.py
│  ├─ style_mapper.py
│  ├─ docx_writer.py
│  └─ types.py
├─ skill/
│  └─ SKILL.md
├─ tests/
└─ requirements.txt
```

## 4. 配置说明

复制示例配置：

```powershell
Copy-Item .\config\model.example.yaml .\config\model.yaml
```

编辑 `config/model.yaml`：

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key_env: "OPENAI_API_KEY"
  model: "gpt-4.1-mini"
  timeout: 30
  max_retries: 2

equation:
  mml2omml_xsl: "C:\\Program Files (x86)\\Microsoft Office\\Office14\\MML2OMML.XSL"

output:
  failure_placeholder: "[公式转换失败]"
```

你可以二选一设置密钥：
- 在配置里直接写 `api_key`
- 使用环境变量（推荐）：`api_key_env: "OPENAI_API_KEY"`

设置环境变量示例：

```powershell
$env:OPENAI_API_KEY = "你的API Key"
```

## 5. 运行转换

```powershell
py -3.10 .\scripts\pipeline.py `
  --input-md .\example\input.md `
  --template-docx .\example\template.docx `
  --output-docx .\example\out.docx `
  --config .\config\model.yaml `
  --log .\example\report.json
```

参数说明：
- `--input-md`：输入 Markdown 路径
- `--template-docx`：参考样式模板 DOCX
- `--output-docx`：输出 DOCX 路径
- `--config`：YAML 配置路径（可选，不传则使用内置默认）
- `--log`：报告 JSON 路径（可选）

## 6. 输入输出规则（重要）

1. 文本保持：非公式文本不做语义改写。  
2. Markdown 支持：解析标题和列表；其他内容按原文写入。  
3. 公式识别：仅处理反引号中的内容，且需通过“数学表达式”规则判定。  
4. 非公式反引号：保持为原样文本（例如 `` `print(x)` ``）。  
5. 失败策略：单个公式失败写占位符，不影响整篇生成。  
6. 样式来源：优先复用模板中的标题、正文、列表样式及段落属性。  

## 7. 结果报告（report.json）

报告字段示例：

```json
{
  "total_formula_candidates": 3,
  "formula_success": 2,
  "formula_failed": 1,
  "failures": [
    {
      "expression": "E = ...",
      "line": 12,
      "stage": "llm_latex",
      "error": "..."
    }
  ]
}
```

常见 `stage`：
- `llm_latex`：大模型转 LaTeX 失败
- `omml_render`：LaTeX 转 OMML 失败

## 8. 运行测试

```powershell
py -3.10 -m pytest -q
```

当前包含：
- 公式识别单测
- Markdown 解析单测
- 公式渲染单测
- 全流程集成测试

## 9. 常见问题

1. 报错 `Missing llm api key`  
检查 `config/model.yaml` 的 `api_key` 或环境变量是否生效。

2. 报错 `MML2OMML XSL not found`  
确认 Office 路径是否存在 `MML2OMML.XSL`，并更新 `equation.mml2omml_xsl`。

3. 为什么某些反引号内容没有转公式  
因为被规则判定为代码/非数学表达式，设计上不会调用大模型。

4. 为什么公式显示为占位符  
该公式在 LaTeX 规范化或 OMML 渲染阶段失败，请查看 `report.json` 的失败明细。

## 10. 后续扩展

当前核心逻辑已经与 UI 解耦，后续可直接套壳为桌面应用（如 PySide6），只需把 GUI 表单参数传给 `scripts/pipeline.py` 或对应 Python 接口，无需改业务核心。
