# EFT 现实主义数值生成器

面向 SPT Realism 物品补丁的批量数值生成工具。当前版本为 v3.55，主流程以 generate_realism_patch.py 为核心，支持多输入格式识别、模板重建、武器/附件/弹药/装备规则重算、按源文件导出，以及生成后审计。

## 项目定位

- 读取 input/ 下的 JSON 物品数据，并结合 现实主义物品模板/ 重建为 Realism 兼容补丁。
- 支持 CURRENT_PATCH、STANDARD、CLONE、ITEMTOCLONE、VIR、TEMPLATE_ID 六类输入。
- 输出保持 input/ 的相对目录结构，并按源文件聚合导出到 output/。
- 规则配置已拆分到独立文件，日常调参不需要改主脚本。

## 当前版本重点

- 弹药霰弹基础档位已细分为 shotgun_12g、shotgun_20g、shotgun_23x75，并保留 shotgun_shell 作为未知口径霰弹的兼容兜底档。
- 弹药 profile 推断新增霰弹载荷兜底逻辑，名称只带 buckshot、flechette、slug、shrapnel 等语义时不再误落入步枪默认档。
- 弹药最终区间应用已为 PenetrationPower 增加 1 到 130 的硬限制，避免低穿霰弹在增量叠加后出现 0 或负数。
- tests/test_ammo_rules.py 当前覆盖 6 条弹药回归用例；本轮全量生成后的输出审计保持 0 违规、0 警告。

## 目录结构

```text
Realism-patch-Generator/
├── generate_realism_patch.py                 # 主生成器
├── generator_static_data.py                  # 静态映射、默认模板、特殊字段配置
├── weapon_rule_ranges.py                     # 武器一级规则
├── weapon_refinement_rules.py                # 武器二级细分规则
├── attachment_rule_ranges.py                 # 附件规则
├── ammo_rule_ranges.py                       # 弹药三层规则
├── gear_rule_ranges.py                       # 装备规则
├── audit_output_rule_violations.py           # 输出审计脚本
├── tests/
│   └── test_name_extraction.py               # 名称回填回归测试
├── 现实主义数值生成器.bat                    # Windows 启动入口
├── input/                                    # 输入 JSON
├── output/                                   # 生成结果（每次运行前会清空）
├── audit_reports/                            # 审计报告输出目录
└── 现实主义物品模板/                         # 模板库
```

## 环境要求

- Python 3.8 及以上
- 无第三方运行依赖，全部使用标准库
- Windows 用户可直接双击 现实主义数值生成器.bat

批处理当前会优先使用 .venv/Scripts/python.exe；若项目内虚拟环境不存在，再回退到系统 python。

## 快速开始

如果你只是想直接出补丁，走下面的“路径 A”。
如果你主要是在调规则范围，优先走“路径 B”，效率更高。

### 路径 A：直接生成补丁

#### 1. 准备输入

将待处理 JSON 放入 input/，支持任意层级子目录。

#### 2. 运行生成器

Windows：

```text
双击 现实主义数值生成器.bat
```

命令行：

```powershell
.\.venv\Scripts\python.exe generate_realism_patch.py
```

### 路径 B：先调规则再生成

如果你不想直接改 Python 规则文件，可以使用图形界面编辑器：

Windows：

```text
双击 规则范围编辑器.bat
```

命令行：

```powershell
.\.venv\Scripts\python.exe rule_range_editor.py
```

GUI 当前支持直接编辑以下规则源中的二元范围值：

- weapon_rule_ranges.py
- weapon_refinement_rules.py
- attachment_rule_ranges.py
- gear_rule_ranges.py
- ammo_rule_ranges.py

编辑方式：

- 左侧按规则类别和档位浏览
- 右侧双击“最小值 / 最大值”直接修改
- 选中任意字段后，下方会显示字段作用、数值方向提示和当前规则类别说明
- 点击“保存全部”后会写回原始规则文件，并自动备份本次改动涉及的规则文件
- 点击“生成补丁”可直接使用当前环境运行 generate_realism_patch.py，一键产出 output 结果
- 保存逻辑只替换范围值元组，尽量保留原文件注释和结构

### 结果查看

- 输出目录固定为 output/
- 运行前会自动清空旧结果
- 输出路径保留 input/ 相对目录结构

命名规则：

- 默认输出为 原文件名_realism_patch.json
- 当同一源文件内成功处理条目中 CURRENT_PATCH 占比大于 50% 时，输出保持原文件名

### 4. 可选审计

```powershell
.\.venv\Scripts\python.exe audit_output_rule_violations.py
```

默认报告输出到 audit_reports/output_rule_audit.json。

审计说明：

- 默认聚焦武器、附件、弹药、装备
- consumable/cosmetic 不作为规则审计重点
- category=mod_profile_unresolved 的附件条目会被忽略，不计入“未能校验附件范围”结果

### 5. 可选回归测试

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_name_extraction
```

该测试用于确认 CURRENT_PATCH、STANDARD、CLONE、ITEMTOCLONE、VIR 的名称提取和审计回读逻辑未回退。

如本轮改动涉及 gear 规则，补跑：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gear_rules
```

该测试用于确认装备 profile 推断、插板/头盔/胸挂/背包等二级细分，以及 gear 区间应用逻辑未回退。

## 支持的输入格式

| 格式 | 典型特征 | 当前用途 |
| ------ | ---------- | ---------- |
| CURRENT_PATCH | 包含 $type 与 ItemID | 直接以输入对象为基线重算 |
| STANDARD | 包含 parentId 或 itemTplToClone | 常规第三方补丁格式 |
| CLONE | 包含 clone | 从模板或同文件引用链继承 |
| ITEMTOCLONE | 包含 ItemToClone | 常见常量式模板引用 |
| VIR | 包含 item._id / item._parent | 兼容 VIR 风格数据 |
| TEMPLATE_ID | 包含 TemplateID 或模板引用 | 直接按模板重建 |

## 规则入口

日常调参优先改以下文件：

- weapon_rule_ranges.py：武器一级基础区间
- weapon_refinement_rules.py：武器口径与枪托二级修正
- attachment_rule_ranges.py：附件档位区间
- ammo_rule_ranges.py：弹药三层规则
- gear_rule_ranges.py：装备档位区间

仅在以下场景需要改 generator_static_data.py：

- 新增 parentId 到模板文件的映射
- 新增字符串类型到标准 parentId 的映射
- 调整默认模板或特定 ModType 补字段策略

仅在以下场景需要改 generate_realism_patch.py：

- 新增一种输入格式
- 调整识别优先级
- 调整导出策略或 CURRENT_PATCH 占比阈值
- 调整启发式规则或全局夹紧逻辑

## 输出与审计工作流

推荐顺序：

1. 先用少量输入文件验证规则变更
2. 运行生成器，检查 output/ 的文件名和目录结构
3. 运行审计脚本查看越界项或未命中规则项
4. 必要时运行名称回归测试
5. 确认无误后再跑全量输入

## 常见问题

### 运行失败

- 优先确认 Python 版本至少为 3.8
- 若双击批处理失败，先检查项目内 .venv 是否存在
- 若命令行方式失败，建议直接使用 .venv 中的 python.exe

### 有些物品被跳过

- 常见原因是模板缺失、输入字段不足、格式不可识别
- 先看控制台输出中的“跳过”原因

### 文件名为什么有的带后缀，有的不带

- 这是当前固定导出策略
- 某源文件内 CURRENT_PATCH 占比超过 50% 时保持原文件名

### 想新增模板映射但不想碰主流程

- 先看 generator_static_data.py
- 多数 parentId / 默认模板 / 名称映射类改动都已经转移到这里

## 相关文档

- CHANGELOG.md：完整版本记录
- 现实主义数值生成器快速入门.md：最短的日常操作路径
- 现实主义数值生成器使用说明.md：面向 GUI + 命令行的总览说明
- 现实主义数值生成器详细使用说明.md：完整工作流与排错说明
- 现实主义数值生成器高级配置指南.md：深度调参与结构说明
- 武器属性规则指南.md：武器规则说明
- 附件属性规则指南.md：附件规则说明
- 弹药属性规则指南.md：弹药规则说明
- 装备属性规则指南.md：装备规则说明
- 规则文件与文档同步对照清单.md：发版前同步清单

## 版本记录

当前版本：v3.55

本轮更新重点：

- 霰弹规则已拆分为 12g、20g、23x75 三档，原 shotgun_shell 仅保留为兼容兜底
- 未显式写出霰弹口径的载荷型弹药现在会落入 shotgun_shell，而不会回退到步枪默认档
- 弹药穿深结果已统一硬限制到 1 到 130，本轮弹药回归测试与全量审计均已通过

完整历史请查看 CHANGELOG.md。
