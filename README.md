# city-commute-mvp

通过命令行输入中国城市名称，生成 3–5 条模拟通勤/城市出行情景及第一人称内心独白。终端显示易读文本，同时保存为 UTF-8 JSON。执行结束即退出，无需启动后台服务。

**当前路线为模拟场景，不是实际通勤统计，也不能用于导航。** 北京、上海、广州、深圳有人工地点对种子；其他城市使用明确标注的占位地点。人物、目的、难点和评分均为规则假设，未核验真实线路、换乘、时长或热门程度。

## 安装与运行

要求 Python 3.11+，在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m city_commute --city 北京
```

默认使用离线 Mock，不需要密钥，不访问外部服务。已安装项目后，也可使用 `city-commute --city 北京`（需激活虚拟环境或使用其 Scripts 下的命令）。

Linux/macOS：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/python -m city_commute --city 北京
```

指定数量、独白样式和输出文件：

```powershell
.\.venv\Scripts\python.exe -m city_commute --city 上海 --routes 5 --sentences 5 --min-chars 20 --max-chars 30 --output outputs/shanghai.json
```

查看参数：

```powershell
.\.venv\Scripts\python.exe -m city_commute --help
```

## 参数与输出

| 参数 | 行为 |
| --- | --- |
| `--city` | 必填，城市中文名称，接受“北京市”等市后缀，名称本身未核验 |
| `--routes` | 3–5，默认 4 |
| `--sentences` | 1–12，默认 6 |
| `--min-chars` / `--max-chars` | 10–80，默认 20/30，最小值不得大于最大值 |
| `--output` | JSON 路径，默认 `outputs/城市_时间戳.json` |
| `--data-provider` | `mock` 或 `osm_wikidata`；后者尚未实现，会明确报错 |
| `--llm-provider` | `mock` 或 `openai_compatible` |

未指定的参数读取 Settings / `.env` / 进程环境。部分覆盖样式参数时，其余值沿用配置。进程环境优先于 `.env`，显式命令行参数优先于对应配置。
默认输出目录可通过 `COMMUTE_OUTPUT_DIR` 配置，相对路径相对于执行时的工作目录，文件名时间戳使用本机时间。指定文件已存在时会报错，避免覆盖。需要新文件时换一个路径。

JSON 同时保存易读文本和结构化数据：

```json
{
  "display_text": "北京 · 模拟通勤场景（4条）\n说明：……\n路线 1：……\n模拟人物：……\n内心独白（模拟）：……",
  "city": {"name": "北京", "country": "CN", "seed_available": true, "identity_verified": false},
  "routes": [],
  "narrative_options": {"sentence_count": 6, "min_chars": 20, "max_chars": 30},
  "warnings": ["路线为模拟场景，未核验真实线路与换乘"]
}
```

以上为结构示意，实际 `routes` 包含 3–5 条完整路线：起终点、场景、人物、目的、可能难点、规则评分、独白句子和来源。`display_text` 是终端中显示的完整文本，JSON 文件中的换行按标准 JSON 转义保存，解析后就是多行文字。中文字符直接保存，不转义为 Unicode 编码。
`route_verified=false`、`difficulties_verified=false`、`monologue.simulated=true`、`geometry=null` 保留证据边界。枢纽到景区属于广义城市出行，并非严格日常通勤。

退出码：0 成功；2 参数/配置错误；1 生成或文件保存失败；130 用户中断。失败时错误写入 stderr，不静默切换 Mock，不生成冒充成功的结果。已有输出文件保持原样。

## LLM 与配置

核心参数集中在 `src/city_commute/config.py`，环境变量前缀为 `COMMUTE_`，完整示例见 `.env.example`。密钥仅通过 `.env` 或环境变量提供，不作为命令行参数、不写入结果 JSON。

启用实际 OpenAI 兼容模型：

```dotenv
COMMUTE_LLM_PROVIDER=openai_compatible
COMMUTE_LLM_BASE_URL=https://your-provider.example/v1
COMMUTE_LLM_API_KEY=your-key
COMMUTE_LLM_MODEL=your-model
```

地址加 `/chat/completions`，要求服务支持项目已有的 Chat Completions 请求/响应格式。真实调用会发送模拟场景到配置的服务商，可能产生费用；格式失败默认重试一次，网络失败直接报错。未验证具体外部服务的兼容性。

独白默认 6 句、每句 20–30 汉字。字数按 Unicode U+4E00–U+9FFF 计数，标点、数字、字母不计。每句须包含“我”。离线模板在自定义较窄范围下可能截断句意，超过 6 句时循环模板；实际 LLM 输出不截断，不合格式则重试/报错。格式验证不证明内容事实正确。

## 项目结构

```text
src/city_commute/
  __main__.py         python -m 入口
  cli.py              参数解析、错误处理、生成调度
  output.py           易读文本与 JSON 文件保存
  config.py           集中配置
  models.py           城市、地点、场景、路线、独白与生成参数
  service.py          数据 → 规则排序 → 独白 → 结果
  scoring.py          可解释加权评分与场景覆盖
  llm.py              Mock 和 OpenAI 兼容独白模块
  providers/          独立的数据提供者、Mock 和真实数据占位
  data/seeds.json     四城市人工地点对
 tests/               命令行、核心模块及模拟 LLM 测试
 docs/design.md       设计与第二阶段接入计划
```

每城五个 Mock 候选，按地标、场景、难点适配性加权（默认 0.5/0.3/0.2），优先覆盖不同场景再补齐。同分按稳定 ID 排序。特征与评分为人工演示设定，不是客流或真实知名度数据。GIS 库位于可选 `geo` 依赖中，当前不需要安装。

## 测试与验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m city_commute --city 北京 --output outputs/beijing.json
```

测试使用 Mock 数据和 HTTPX MockTransport，不访问外部服务、不消耗 LLM 额度。覆盖四城市端到端、未知城市占位、句数/字数配置、错误输入、JSON 文件读写、已有文件保护、实际模块入口、评分、LLM 请求/重试/失败退出。
第二阶段真实 OSM/Wikidata 接入计划见 [设计文档](docs/design.md)。

本次验证环境为 Windows / Python 3.13.5：25 项测试通过，实际命令行生成及 JSON 保存成功。未调用真实 LLM 或地理数据接口，未进行 Python 3.11 环境矩阵测试。
