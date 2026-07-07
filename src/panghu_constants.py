"""胖虎AI客户端 · 集中常量（从 panghu_ai_client.py 抽出，见 AGENTS.md 拆分说明）。

纯数据：App 标识、服务端 URL、通讯软件/增值业务选项、UI 设计 token、流程步骤与模块导航配置。
panghu_ai_client 通过 `from panghu_constants import *` 引入，引用点不变。
"""
import os


APP_NAME = "胖虎AI客户端"
APP_VERSION = "1.0.16"
HTTP_USER_AGENT = f"PanghuAI-Client/{APP_VERSION}"
# 本地联调开关（仅开发/集成测试用）：设置 PANGHU_DEV_BASE_URL_OVERRIDE 可将
# 全部服务端地址指向本地联调网关。生产构建不设置此环境变量，行为不变；
# 启动时若覆盖生效会在日志和窗口标题打出醒目提示，防止误用。
PANGHU_DEV_BASE_URL_OVERRIDE = os.environ.get("PANGHU_DEV_BASE_URL_OVERRIDE", "").strip().rstrip("/")
DEFAULT_BASE_URL = PANGHU_DEV_BASE_URL_OVERRIDE or "https://aitokenapi.cc"
DEFAULT_MODEL = "gpt-5.5"
CODEX_PROVIDER_NAME = "panghuAI"
CODEX_BASE_URL = f"{DEFAULT_BASE_URL}/v1"
CLAUDE_CODE_BASE_URL = DEFAULT_BASE_URL
TEMP_OPENAI_ACCESS_SECONDS = 600
TEMP_OPENAI_ACCESS_MAX_SECONDS = 600
AGENT_DIALOGUE_PROBE_PROMPT = "请用一句中文回复：胖虎AI配置验证成功"

GITHUB_RELEASE_API = "https://api.github.com/repos/dashuaiisme/panghu-ai-client/releases/latest"
PUBLIC_UPDATE_MANIFEST_URL = f"{DEFAULT_BASE_URL}/deployer/latest.json"
WINDOWS_RELEASE_DIR_NAME = APP_NAME
WINDOWS_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Windows.zip"
WINDOWS_RELEASE_ASSET_ALIASES = (
    WINDOWS_RELEASE_ASSET_NAME,
)
MAC_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac.zip"
MAC_RELEASE_ASSET_ALIASES = (
    MAC_RELEASE_ASSET_NAME,
)
MAC_APPLE_SILICON_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac-AppleSilicon.zip"
MAC_INTEL_RELEASE_ASSET_NAME = f"{WINDOWS_RELEASE_DIR_NAME}-Mac-Intel.zip"
MAC_APPLE_SILICON_RELEASE_ASSET_ALIASES = (
    MAC_APPLE_SILICON_RELEASE_ASSET_NAME,
    MAC_RELEASE_ASSET_NAME,
)
MAC_INTEL_RELEASE_ASSET_ALIASES = (
    MAC_INTEL_RELEASE_ASSET_NAME,
)
LOGIN_URL = f"{DEFAULT_BASE_URL}/api/user/login?turnstile="
DEPLOYER_ACTIVATE_URL = f"{DEFAULT_BASE_URL}/api/deployer/activate"
DEPLOYER_MANIFEST_URL = f"{DEFAULT_BASE_URL}/api/deployer/manifest"
REGISTER_URL = f"{DEFAULT_BASE_URL}/register"
PANGHU_HOME_URL = DEFAULT_BASE_URL
KEY_CREATE_URL = f"{DEFAULT_BASE_URL}/console/token"
CONSOLE_URL = f"{DEFAULT_BASE_URL}/console"
BUY_URL = f"{DEFAULT_BASE_URL}/buy"
AFFILIATE_URL = f"{DEFAULT_BASE_URL}/affiliate"
SIM_CONTROL_URL = "https://sim.aitokenapi.cc"
AGENT_CENTER_URL = f"{DEFAULT_BASE_URL}/agent"
AGENT_CUSTOMERS_URL = f"{DEFAULT_BASE_URL}/agent/customers"
AGENT_TOKEN_COMM_URL = f"{DEFAULT_BASE_URL}/agent/token-commission"
AGENT_ACTIVATION_COMM_URL = f"{DEFAULT_BASE_URL}/agent/activation-commission"
AGENT_INSTALL_COMM_URL = f"{DEFAULT_BASE_URL}/agent/install-commission"
AGENT_PROXY_URL = f"{DEFAULT_BASE_URL}/agent/proxy"
AGENT_RULES_URL = f"{DEFAULT_BASE_URL}/agent/rules"
AGENT_JOIN_URL = f"{DEFAULT_BASE_URL}/agent/join"
VALUE_ADDED_URLS = {
    "gpt_plus": f"{DEFAULT_BASE_URL}/services?entry=gpt-plus",
    "phone_card": f"{DEFAULT_BASE_URL}/services?entry=phone-card",
    "sms_code": SIM_CONTROL_URL,
}
COMMUNICATION_SOFTWARE_LINK_AGENT_OPTIONS = ("codex", "claude_code", "openclaw", "hermes")
COMMUNICATION_SOFTWARE_LINK_CHANNEL_OPTIONS = ("qq_bot", "weixin", "feishu", "dingtalk", "wecom")
COMMUNICATION_SOFTWARE_LINK_AGENT_SOURCE_OPTIONS = ("existing_local_agent", "historical_delivery", "current_delivery", "manual_review")
COMMUNICATION_SOFTWARE_LINK_GATEWAY_MODE_OPTIONS = ("official_bot", "customer_bot", "manual_bridge")
COMMUNICATION_SOFTWARE_LINK_DEFAULT_PROMPT = "请回复连接通讯软件验收成功"
COMMUNICATION_SOFTWARE_LINK_LOCAL_EVIDENCE_BASE_URL = "local://communication-software-link/evidence"
COMMUNICATION_SOFTWARE_LINK_PLATFORM_AUTH_MAX_POLLS = 24
COMMUNICATION_SOFTWARE_LINK_PLATFORM_AUTH_POLL_SECONDS = 5
INVITE_QUERY_KEYS = ("invite", "invite_code", "aff", "aff_code", "ref", "referral", "referral_code")
CODEX_WINDOWS_STORE_URL = "https://get.microsoft.com/installer/download/9PLM9XGG6VKS?cid=website_cta_psi"
CODEX_DOWNLOAD_URL = "https://developers.openai.com/codex/"
CLAUDE_CODE_DOCS_URL = "https://code.claude.com/docs/en/quickstart"
OPENCLAW_DOCS_URL = "https://docs.openclaw.ai/start/getting-started"
HERMES_DOCS_URL = "https://hermes-agent.nousresearch.com/docs/zh-Hans/getting-started/installation"
GEMINI_AGY_DOCS_URL = "https://antigravity.google/"
OFFICIAL_PACKAGE_SUFFIXES = (".msixbundle", ".msix", ".appx", ".appxbundle", ".appinstaller")
PANGHU_AGENTS_START = "<!-- PANGHUAI_CODEX_RULES_START -->"
PANGHU_AGENTS_END = "<!-- PANGHUAI_CODEX_RULES_END -->"
APP_BG = "#e8e8ed"
SURFACE_BG = "#f5f5f7"
SIDEBAR_BG = "#ebebec"
CARD_BG = "#ffffff"
PANEL_BG = "#f7f7f8"
INK = "#1d1d1f"
SECONDARY = "#424245"
MUTED = "#86868b"
FAINT = "#b0b0b5"
PRIMARY = "#0071e3"
PRIMARY_HOVER = "#0077ed"
PRIMARY_DARK = "#0062c0"
PRIMARY_LIGHT = "#eff7ff"
PRIMARY_TINT = "#e8f2ff"
ACCENT = "#1a7f37"
BORDER = "#d2d2d7"
LIGHT_BORDER = "#e5e5e7"
WARNING_BG = "#fff7df"
GOLD = "#b06000"
GOLD_SOFT = "#fff7df"
LOCKED_BG = "#f1f3f4"
WAIT_BG = "#f1f3f4"
WAIT_BORDER = "#dadce0"
SUCCESS_BG = "#e6f4ea"
SUCCESS_BORDER = "#ceead6"
INFO_BG = "#eaf4ff"
FAIL_BG = "#fdebe5"
FAIL_BORDER = "#fad2cf"
FAIL = "#c5221f"
RUNNING = "#b06000"
SUCCESS = "#1a7f37"
NEUTRAL_DOT = "#9a9aa0"
INPUT_BG = "#ffffff"
LOG_BG = "#1d1d1f"
LOG_FG = "#f5f5f7"
SEGMENTED_BG = "#e3e3e6"
SEGMENTED_ACTIVE = "#ffffff"
APP_FRAME_BG = SURFACE_BG
APP_FRAME_BORDER = BORDER
TOPBAR_HEIGHT = 52
LEFT_PANEL_WIDTH = 220
RIGHT_PANEL_WIDTH = 300
FLOW_STEPS = (
    (1, "创建/填写 API Key", "填入调用令牌并测试"),
    (2, "检测环境", "先排查电脑和风险工具"),
    (3, "选择 Agent", "选择要交付的 Agent"),
    (4, "执行安装", "按引导安装并配置"),
    (5, "写入配置", "写入网关、Key 和模型"),
    (6, "启动检测", "确认入口可以打开"),
    (7, "最小中文对话", "确认能直接中文对话"),
    (8, "功能验收矩阵", "逐项确认是否达标"),
    (9, "基础交付验收", "完成基础验收后收口"),
    (10, "连接通讯软件", "配置通讯软件通道"),
    (11, "连接通讯软件交付验收", "通讯软件发送消息验证"),
)

MODULE_AGENT = "agent"
MODULE_SITE = "site"
MODULE_VALUE_ADDED = "value_added"
MODULE_COURSES = "courses"
TOP_MODULES = (
    (MODULE_AGENT, "配置Agent", "安装配置与验收"),
    (MODULE_SITE, "胖虎AI网站", "控制台、Key、充值"),
    (MODULE_VALUE_ADDED, "增值业务", "账号会员与服务"),
    (MODULE_COURSES, "代理中心", "代理分销与返佣"),
)
MODULE_SIDE_NAV_ITEMS = {
    MODULE_AGENT: tuple((str(idx), title, subtitle) for idx, title, subtitle in FLOW_STEPS),
    MODULE_SITE: (
        ("account", "控制台", "打开胖虎AI首页或控制台"),
        ("key", "创建 API Key", "进入令牌管理页面"),
        ("recharge", "充值购买", "跳转官方在线购买页"),
        ("register", "推广返佣", "查看邀请码与返佣入口"),
    ),
    MODULE_VALUE_ADDED: (
        ("gpt_plus", "GPT 账号会员", "Plus、Team、Pro 服务入口"),
        ("phone_card", "国外手机卡", "海外号码与通信服务"),
        ("sms_code", "接码控制台", "手机号接码控制中心"),
    ),
    MODULE_COURSES: (
        ("agent_home", "代理总览", "代理等级、邀请入口与结算摘要"),
        ("agent_customers", "下游客户", "查看服务端下游客户归因"),
        ("agent_token_comm", "token 返佣", "下游 token 消费返佣摘要"),
        ("agent_activation_comm", "激活返佣", "下游付费激活返佣摘要"),
        ("agent_install_comm", "安装返佣", "下游客户付费安装 Agent 返佣"),
        ("agent_proxy", "工具代理后端", "进入工具代理业务后台"),
        ("agent_join", "招商介绍", "查看代理公开招商政策与加入条件"),
        ("agent_rules", "代理规则", "查看结算、升级与风控规则"),
    ),
}
MODULE_PAGE_META = {
    MODULE_SITE: {
        "account": ("胖虎AI控制台", CONSOLE_URL, "主工作区直接显示胖虎AI首页或控制台入口，登录后可继续管理账号、额度和节点。"),
        "key": ("令牌管理", KEY_CREATE_URL, "从网站服务端打开令牌管理页面，创建或复制当前买家自己的 API Key。"),
        "recharge": ("在线购买", BUY_URL, "从网站服务端打开官方在线购买页，完成套餐、余额或升级购买。"),
        "register": ("推广返佣", AFFILIATE_URL, "从网站服务端打开推广返佣页，查看邀请码、返佣记录和邀请入口。"),
    },
    MODULE_VALUE_ADDED: {
        "gpt_plus": ("GPT 账号会员", VALUE_ADDED_URLS["gpt_plus"], "进入增值业务页的 GPT 账号会员分区，具体上架状态和价格以服务端为准。"),
        "phone_card": ("国外手机卡", VALUE_ADDED_URLS["phone_card"], "进入增值业务页的海外号码与通信服务分区，所有商品信息由网站服务端控制。"),
        "sms_code": ("接码控制台", VALUE_ADDED_URLS["sms_code"], "打开手机号接码控制中心；价格、订单、可用号码和短信回传仍以服务端为准。"),
    },
    MODULE_COURSES: {
        "agent_home": ("代理总览", AGENT_CENTER_URL, "查看当前代理状态、等级、邀请入口和结算摘要。"),
        "agent_customers": ("下游客户", AGENT_CUSTOMERS_URL, "查看下游客户归因、绑定时间和服务端客户摘要。"),
        "agent_token_comm": ("token 返佣", AGENT_TOKEN_COMM_URL, "查看下游 token/API 消费产生的返佣摘要。"),
        "agent_activation_comm": ("激活返佣", AGENT_ACTIVATION_COMM_URL, "查看下游付费激活、充值或购买产生的返佣摘要。"),
        "agent_install_comm": ("安装返佣", AGENT_INSTALL_COMM_URL, "查看下游客户付费安装 Agent 服务产生的返佣摘要。"),
        "agent_proxy": ("工具代理后端", AGENT_PROXY_URL, "进入工具代理业务后台，管理代理业务入口和服务端状态。"),
        "agent_join": ("招商介绍", AGENT_JOIN_URL, "查看代理公开招商政策、合作优势与加入条件。"),
        "agent_rules": ("代理规则", AGENT_RULES_URL, "查看代理费用、升级、返佣、提现、冻结和冲正规则。"),
    },
}
MODULE_ACTION_CARDS = {
    MODULE_SITE: {
        "account": (
            ("先看哪里", "优先看控制台首页、额度余额、节点状态和当前账号信息。"),
            ("适合做什么", "登录后直接继续管理控制台，不需要再单独打开第三方浏览器。"),
            ("客服怎么指引", "客服只需要让客户在这里完成控制台里的下一步操作。"),
            ("注意事项", "控制台内的业务状态以胖虎AI网站服务端返回为准。"),
        ),
        "key": (
            ("现在要做什么", "进入令牌管理后创建新 Key，复制完整的 sk- 内容回来填写。"),
            ("做完看哪里", "返回本工具第一步，粘贴后点“保存并测试 Key”。"),
            ("客服确认点", "确认 Key 属于当前买家账号，且账户已充值或有可用额度。"),
            ("安全边界", "API Key 不写入执行日志；profile.json 只保存账号提示、Key、模型和界面偏好。"),
        ),
        "recharge": (
            ("现在要做什么", "在官方在线购买页完成套餐购买、余额充值或升级付款。"),
            ("做完看哪里", "支付完成后回到工具，再继续创建 Key 或执行部署步骤。"),
            ("客服确认点", "若余额仍不足，先刷新网站订单状态，再继续本地配置。"),
            ("注意事项", "价格、次数、有效期、设备数都以服务端页面为准，不在本地写死。"),
        ),
        "register": (
            ("现在要做什么", "打开推广返佣页，查看邀请码、推广链接和返佣记录。"),
            ("做完看哪里", "需要创建新的胖虎AI账号时，也从这里继续进入返佣或邀请相关入口。"),
            ("客服确认点", "代理身份、邀请码绑定和返佣结算全部以网站服务端为准。"),
            ("注意事项", "邀请码、返佣和代理身份均由胖虎AI网站服务端处理。"),
        ),
    },
    MODULE_VALUE_ADDED: {
        "gpt_plus": (
            ("服务入口", "展示 GPT Plus、Team、Pro 等会员服务的独立入口。"),
            ("订单承接", "具体服务能否购买、如何购买，以服务端上架内容为准。"),
            ("客服协同", "客户可把本页记录复制给客服，继续人工确认套餐细节。"),
            ("交付边界", "本地工具不保存这类第三方账号的登录态或支付信息。"),
        ),
        "phone_card": (
            ("服务入口", "展示国外手机卡、海外通信号码和辅助服务入口。"),
            ("适用场景", "用于 OpenAI、Claude 等海外平台注册或长期通信场景。"),
            ("客服协同", "具体国家、库存与价格只从网站服务端读取。"),
            ("交付边界", "客户端不硬编码国家库存、价格或开卡规则。"),
        ),
        "sms_code": (
            ("控制台入口", "打开 sim 子域名的手机号接码控制中心，承接号码托管和接码工作台。"),
            ("平台绑定", "用户开始接码前必须选择 OpenAI、Google 等本次接收平台。"),
            ("短信回传", "验证码必须匹配用户、号码、当前会话、时间窗口和本次平台。"),
            ("服务状态", "可用号码、订单、价格、失败处理和退款规则以服务端返回为准。"),
        ),
    },
    MODULE_COURSES: {
        "agent_home": (
            ("先看哪里", "优先查看当前代理等级、邀请入口、下游数量和结算摘要。"),
            ("收益来源", "服务端区分 token 返佣、激活返佣和安装返佣三类收入。"),
            ("如何邀请", "通过专属邀请链接或注册邀请码绑定下游客户，已有上级不覆盖。"),
            ("结算边界", "所有收益、冻结、冲正和提现状态以服务端账本为准。"),
        ),
        "agent_customers": (
            ("数据来源", "下游客户归因只来自胖虎AI服务端，不从本地邀请码记录推算。"),
            ("客户分类", "可按注册、付费激活、已安装 Agent 服务等状态查看。"),
            ("跟进策略", "客服可结合后端诊断码和客户状态辅助交付。"),
            ("绑定边界", "已有上级代理的客户不能被新邀请码覆盖。"),
        ),
        "agent_token_comm": (
            ("收益类型", "展示下游 token/API 真实消费产生的返佣摘要。"),
            ("事件来源", "以服务端结算后的真实消费事件为准，重复事件不重复入账。"),
            ("结算周期", "默认 T+7 从待结算转为可结算，具体以后台设置为准。"),
            ("状态说明", "退款、异常消费或风控命中后可冻结或冲正。"),
        ),
        "agent_activation_comm": (
            ("收益类型", "展示下游付费激活、购买或充值产生的返佣摘要。"),
            ("订单快照", "佣金按订单发生时的代理链路和返佣规则快照计算。"),
            ("结算周期", "默认 T+7 进入可结算，后台可按业务策略调整。"),
            ("异常处理", "订单撤销或退款后必须写入冲正记录。"),
        ),
        "agent_install_comm": (
            ("安装返佣", "每当下游客户成功安装并激活一个 Agent，您可获得专属返佣。"),
            ("结算比例", "服务端按实际安装的 Agent 类型和授权节点数量动态计算。"),
            ("状态说明", "需要客户完成“功能验收矩阵”并在本地成功跑通中文对话。"),
            ("注意事项", "已退款或非正常部署的节点不会计入有效安装返佣。"),
        ),
        "agent_proxy": (
            ("后端入口", "工具代理相关后端统一从胖虎AI网站和服务端代理中心进入。"),
            ("服务开关", "哪些代理能力已开放，由服务端和代理后端决定。"),
            ("接入计划", "后续代理工具诊断、回调和售后入口也统一归到这里。"),
            ("注意事项", "客户端只提供入口和状态衔接，不在本地重做代理业务规则。"),
        ),
        "agent_join": (
            ("招募说明", "公开招商页面展示代理合作优势、费用模式和升级路径。"),
            ("加入申请", "代理级别、结算条款和风险控制以服务端规则为准。"),
            ("注意事项", "客户端仅提供招商介绍入口，本地不写死招商费用或分成费率。"),
            ("服务端为准", "所有活动细则、结算及佣金分配比例由胖虎AI服务端定义。"),
        ),
        "agent_rules": (
            ("费用规则", "代理费用、免费开通、付费升级、押金或年费都由管理员后台配置。"),
            ("等级规则", "代理采用 L1-L5 纯五级模型，等级越高可覆盖的下游层级越深。"),
            ("风控说明", "禁止自行邀请自己或利用多账号刷取安装返佣，异常收益可冻结。"),
            ("服务端为准", "所有比例、费率、提现、冲正和待接入状态以胖虎AI服务端实时规则为准。"),
        ),
    },
}
