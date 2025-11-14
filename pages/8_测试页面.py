import streamlit as st
import json
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import copy


class FormatType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"


class PricingUnit(Enum):
    PER_TOKEN = "token"
    PER_CALL = "call"


class Currency(Enum):
    USD = "USD"
    CNY = "CNY"


@dataclass
class FormatConfig:
    format_type: FormatType
    token_consumption: int = 0


@dataclass
class Task:
    name: str
    total_count: int = 1000
    input_formats: List[FormatConfig] = field(default_factory=list)
    output_formats: List[FormatConfig] = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "total_count": self.total_count,
            "input_formats": [
                {"format_type": fmt.format_type.value, "token_consumption": fmt.token_consumption}
                for fmt in self.input_formats
            ],
            "output_formats": [
                {"format_type": fmt.format_type.value, "token_consumption": fmt.token_consumption}
                for fmt in self.output_formats
            ]
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            total_count=data["total_count"],
            input_formats=[
                FormatConfig(FormatType(fmt["format_type"]), fmt["token_consumption"])
                for fmt in data["input_formats"]
            ],
            output_formats=[
                FormatConfig(FormatType(fmt["format_type"]), fmt["token_consumption"])
                for fmt in data["output_formats"]
            ]
        )


@dataclass
class ModelPricing:
    format_type: FormatType
    pricing_unit: PricingUnit
    input_price: float = 0.0
    output_price: float = 0.0
    currency: Currency = Currency.USD
    unit_scale: int = 1000000  # 默认百万token

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        if self.pricing_unit == PricingUnit.PER_TOKEN:
            input_cost = (input_tokens / self.unit_scale) * self.input_price
            output_cost = (output_tokens / self.unit_scale) * self.output_price
        else:  # PER_CALL
            input_cost = self.input_price * (input_tokens > 0)
            output_cost = self.output_price * (output_tokens > 0)
        return input_cost + output_cost


@dataclass
class RateLimit:
    requests_per_minute: Optional[int] = None
    tokens_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None


@dataclass
class AIModel:
    name: str
    supported_inputs: List[FormatType]
    supported_outputs: List[FormatType]
    pricing: List[ModelPricing] = field(default_factory=list)
    rate_limits: RateLimit = field(default_factory=RateLimit)
    is_free: bool = False

    def to_dict(self):
        return {
            "name": self.name,
            "supported_inputs": [fmt.value for fmt in self.supported_inputs],
            "supported_outputs": [fmt.value for fmt in self.supported_outputs],
            "pricing": [
                {
                    "format_type": price.format_type.value,
                    "pricing_unit": price.pricing_unit.value,
                    "input_price": price.input_price,
                    "output_price": price.output_price,
                    "currency": price.currency.value,
                    "unit_scale": price.unit_scale
                }
                for price in self.pricing
            ],
            "rate_limits": {
                "requests_per_minute": self.rate_limits.requests_per_minute,
                "tokens_per_minute": self.rate_limits.tokens_per_minute,
                "requests_per_day": self.rate_limits.requests_per_day
            },
            "is_free": self.is_free
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            supported_inputs=[FormatType(fmt) for fmt in data["supported_inputs"]],
            supported_outputs=[FormatType(fmt) for fmt in data["supported_outputs"]],
            pricing=[
                ModelPricing(
                    format_type=FormatType(price["format_type"]),
                    pricing_unit=PricingUnit(price["pricing_unit"]),
                    input_price=price["input_price"],
                    output_price=price["output_price"],
                    currency=Currency(price["currency"]),
                    unit_scale=price.get("unit_scale", 1000000)
                )
                for price in data["pricing"]
            ],
            rate_limits=RateLimit(
                requests_per_minute=data["rate_limits"].get("requests_per_minute"),
                tokens_per_minute=data["rate_limits"].get("tokens_per_minute"),
                requests_per_day=data["rate_limits"].get("requests_per_day")
            ),
            is_free=data["is_free"]
        )


@dataclass
class AIPlatform:
    name: str
    models: List[AIModel] = field(default_factory=list)
    global_rate_limits: RateLimit = field(default_factory=RateLimit)

    def to_dict(self):
        return {
            "name": self.name,
            "models": [model.to_dict() for model in self.models],
            "global_rate_limits": {
                "requests_per_minute": self.global_rate_limits.requests_per_minute,
                "tokens_per_minute": self.global_rate_limits.tokens_per_minute,
                "requests_per_day": self.global_rate_limits.requests_per_day
            }
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            models=[AIModel.from_dict(model) for model in data["models"]],
            global_rate_limits=RateLimit(
                requests_per_minute=data["global_rate_limits"].get("requests_per_minute"),
                tokens_per_minute=data["global_rate_limits"].get("tokens_per_minute"),
                requests_per_day=data["global_rate_limits"].get("requests_per_day")
            )
        )


class DataManager:
    def __init__(self):
        if 'tasks' not in st.session_state:
            st.session_state.tasks = []
        if 'platforms' not in st.session_state:
            st.session_state.platforms = []

    def add_task(self, task: Task):
        st.session_state.tasks.append(task)

    def update_task(self, index: int, task: Task):
        st.session_state.tasks[index] = task

    def delete_task(self, index: int):
        st.session_state.tasks.pop(index)

    def add_platform(self, platform: AIPlatform):
        st.session_state.platforms.append(platform)

    def update_platform(self, index: int, platform: AIPlatform):
        st.session_state.platforms[index] = platform

    def delete_platform(self, index: int):
        st.session_state.platforms.pop(index)

    def export_data(self) -> Dict[str, Any]:
        return {
            "tasks": [task.to_dict() for task in st.session_state.tasks],
            "platforms": [platform.to_dict() for platform in st.session_state.platforms]
        }

    def import_data(self, data: Dict[str, Any]):
        st.session_state.tasks = [Task.from_dict(task) for task in data["tasks"]]
        st.session_state.platforms = [AIPlatform.from_dict(platform) for platform in data["platforms"]]


class StreamlitUI:
    def __init__(self):
        self.data_manager = DataManager()
        self.setup_page()

    def setup_page(self):
        st.set_page_config(page_title="AI模型成本分析器", layout="wide")
        st.title("🤖 AI模型成本分析器")
        st.markdown("管理AI模型价格并计算任务处理成本")

    def run(self):
        tab1, tab2, tab3 = st.tabs(["任务成本分析", "任务管理", "平台管理"])

        with tab1:
            self.show_cost_analysis()

        with tab2:
            self.manage_tasks()

        with tab3:
            self.manage_platforms()

        # 导入导出功能
        st.sidebar.header("数据管理")
        self.import_export_section()

    def show_cost_analysis(self):
        st.header("任务成本分析")

        if not st.session_state.tasks:
            st.info("请先添加任务配置")
            return

        if not st.session_state.platforms:
            st.info("请先添加AI平台和模型")
            return

        # 选择任务
        task_names = [task.name for task in st.session_state.tasks]
        selected_task_name = st.selectbox("选择要分析的任务", task_names)
        selected_task = next(task for task in st.session_state.tasks if task.name == selected_task_name)

        # 显示任务详情
        st.subheader("任务详情")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**任务名称:** {selected_task.name}")
            st.write(f"**任务总数:** {selected_task.total_count}")

        with col2:
            input_types = ", ".join([fmt.format_type.value for fmt in selected_task.input_formats])
            output_types = ", ".join([fmt.format_type.value for fmt in selected_task.output_formats])
            st.write(f"**输入格式:** {input_types}")
            st.write(f"**输出格式:** {output_types}")

        # 计算并显示兼容的模型
        st.subheader("兼容的模型及成本分析")
        results = []

        for platform in st.session_state.platforms:
            for model in platform.models:
                if self.is_model_compatible(model, selected_task):
                    cost_usd, cost_cny = self.calculate_task_cost(model, selected_task)
                    results.append({
                        "平台": platform.name,
                        "模型": model.name,
                        "是否免费": "是" if model.is_free else "否",
                        "成本(USD)": f"${cost_usd:.6f}" if not model.is_free else "免费",
                        "成本(CNY)": f"¥{cost_cny:.2f}" if not model.is_free else "免费",
                        "速率限制": self.format_rate_limits(model.rate_limits)
                    })

        if results:
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("没有找到兼容的模型")

    def is_model_compatible(self, model: AIModel, task: Task) -> bool:
        # 检查输入格式兼容性
        task_inputs = {fmt.format_type for fmt in task.input_formats}
        if not task_inputs.issubset(set(model.supported_inputs)):
            return False

        # 检查输出格式兼容性
        task_outputs = {fmt.format_type for fmt in task.output_formats}
        if not task_outputs.issubset(set(model.supported_outputs)):
            return False

        return True

    def calculate_task_cost(self, model: AIModel, task: Task) -> tuple[float, float]:
        if model.is_free:
            return 0.0, 0.0

        total_cost_usd = 0.0
        exchange_rate = 7.2  # 假设汇率

        # 计算输入成本
        for input_fmt in task.input_formats:
            pricing = next((p for p in model.pricing if p.format_type == input_fmt.format_type), None)
            if pricing:
                input_tokens = input_fmt.token_consumption * task.total_count
                cost = pricing.calculate_cost(input_tokens, 0)
                if pricing.currency == Currency.CNY:
                    cost /= exchange_rate  # 转换为USD
                total_cost_usd += cost

        # 计算输出成本
        for output_fmt in task.output_formats:
            pricing = next((p for p in model.pricing if p.format_type == output_fmt.format_type), None)
            if pricing:
                output_tokens = output_fmt.token_consumption * task.total_count
                cost = pricing.calculate_cost(0, output_tokens)
                if pricing.currency == Currency.CNY:
                    cost /= exchange_rate  # 转换为USD
                total_cost_usd += cost

        return total_cost_usd, total_cost_usd * exchange_rate

    def format_rate_limits(self, rate_limits: RateLimit) -> str:
        limits = []
        if rate_limits.requests_per_minute:
            limits.append(f"请求/分: {rate_limits.requests_per_minute}")
        if rate_limits.tokens_per_minute:
            limits.append(f"Token/分: {rate_limits.tokens_per_minute}")
        if rate_limits.requests_per_day:
            limits.append(f"请求/天: {rate_limits.requests_per_day}")
        return ", ".join(limits) if limits else "无限制"

    def manage_tasks(self):
        st.header("任务管理")

        # 添加新任务
        with st.expander("添加新任务", expanded=False):
            self.add_task_form()

        # 显示现有任务
        st.subheader("现有任务")
        if not st.session_state.tasks:
            st.info("暂无任务配置")
        else:
            for i, task in enumerate(st.session_state.tasks):
                with st.expander(f"任务: {task.name}"):
                    self.edit_task_form(i, task)

    def add_task_form(self):
        with st.form("add_task_form"):
            name = st.text_input("任务名称*")
            total_count = st.number_input("任务总数", min_value=1, value=1000)

            st.subheader("输入格式配置")
            input_formats = self.format_config_section("input")

            st.subheader("输出格式配置")
            output_formats = self.format_config_section("output")

            if st.form_submit_button("添加任务"):
                if name:
                    task = Task(name=name, total_count=total_count,
                                input_formats=input_formats, output_formats=output_formats)
                    self.data_manager.add_task(task)
                    st.success("任务添加成功!")
                    st.rerun()
                else:
                    st.error("请输入任务名称")

    def format_config_section(self, section_type: str) -> List[FormatConfig]:
        formats = st.multiselect(
            f"选择{section_type}格式",
            [fmt.value for fmt in FormatType],
            key=f"{section_type}_formats"
        )

        format_configs = []
        for fmt in formats:
            token_consumption = st.number_input(
                f"{fmt} token消耗量",
                min_value=0,
                value=100 if fmt == FormatType.TEXT.value else 1000,
                key=f"{section_type}_{fmt}_tokens"
            )
            format_configs.append(FormatConfig(FormatType(fmt), token_consumption))

        return format_configs

    def edit_task_form(self, index: int, task: Task):
        with st.form(f"edit_task_{index}"):
            name = st.text_input("任务名称*", value=task.name)
            total_count = st.number_input("任务总数", min_value=1, value=task.total_count,
                                          key=f"edit_total_{index}")

            # 简化编辑界面，直接显示当前配置
            st.write("**当前输入格式:**")
            for fmt in task.input_formats:
                st.write(f"- {fmt.format_type.value}: {fmt.token_consumption} tokens")

            st.write("**当前输出格式:**")
            for fmt in task.output_formats:
                st.write(f"- {fmt.format_type.value}: {fmt.token_consumption} tokens")

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新任务"):
                    updated_task = Task(name=name, total_count=total_count,
                                        input_formats=task.input_formats,
                                        output_formats=task.output_formats)
                    self.data_manager.update_task(index, updated_task)
                    st.success("任务更新成功!")
                    st.rerun()

            with col2:
                if st.form_submit_button("删除任务"):
                    self.data_manager.delete_task(index)
                    st.success("任务删除成功!")
                    st.rerun()

    def manage_platforms(self):
        st.header("AI平台管理")

        # 添加新平台
        with st.expander("添加新平台", expanded=False):
            self.add_platform_form()

        # 显示现有平台
        st.subheader("现有平台")
        if not st.session_state.platforms:
            st.info("暂无平台配置")
        else:
            for i, platform in enumerate(st.session_state.platforms):
                with st.expander(f"平台: {platform.name}"):
                    self.edit_platform_form(i, platform)

    def add_platform_form(self):
        with st.form("add_platform_form"):
            name = st.text_input("平台名称*")

            st.subheader("平台级速率限制（可选）")
            global_limits = self.rate_limit_section("platform_global")

            st.subheader("添加模型")
            model_name = st.text_input("模型名称")
            supported_inputs = st.multiselect(
                "支持的输入类型",
                [fmt.value for fmt in FormatType],
                key="model_inputs"
            )
            supported_outputs = st.multiselect(
                "支持的输出类型",
                [fmt.value for fmt in FormatType],
                key="model_outputs"
            )

            is_free = st.checkbox("免费模型")

            if not is_free:
                st.subheader("定价配置")
                # 简化定价配置界面
                st.info("在当前版本中，定价配置需要在代码中详细设置")

            model_limits = self.rate_limit_section("model")

            if st.form_submit_button("添加平台和模型"):
                if name and model_name:
                    model = AIModel(
                        name=model_name,
                        supported_inputs=[FormatType(fmt) for fmt in supported_inputs],
                        supported_outputs=[FormatType(fmt) for fmt in supported_outputs],
                        rate_limits=model_limits,
                        is_free=is_free
                    )

                    platform = AIPlatform(name=name, models=[model], global_rate_limits=global_limits)
                    self.data_manager.add_platform(platform)
                    st.success("平台添加成功!")
                    st.rerun()
                else:
                    st.error("请输入平台名称和模型名称")

    def rate_limit_section(self, prefix: str) -> RateLimit:
        col1, col2, col3 = st.columns(3)
        with col1:
            req_per_min = st.number_input("请求/分钟", min_value=0, value=0, key=f"{prefix}_rpm")
        with col2:
            tokens_per_min = st.number_input("Token/分钟", min_value=0, value=0, key=f"{prefix}_tpm")
        with col3:
            req_per_day = st.number_input("请求/天", min_value=0, value=0, key=f"{prefix}_rpd")

        return RateLimit(
            requests_per_minute=req_per_min if req_per_min > 0 else None,
            tokens_per_minute=tokens_per_min if tokens_per_min > 0 else None,
            requests_per_day=req_per_day if req_per_day > 0 else None
        )

    def edit_platform_form(self, index: int, platform: AIPlatform):
        st.write(f"**平台名称:** {platform.name}")
        st.write("**包含模型:**")
        for model in platform.models:
            st.write(f"- {model.name} (输入: {[fmt.value for fmt in model.supported_inputs]}, "
                     f"输出: {[fmt.value for fmt in model.supported_outputs]})")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("删除平台", key=f"delete_platform_{index}"):
                self.data_manager.delete_platform(index)
                st.success("平台删除成功!")
                st.rerun()

    def import_export_section(self):
        st.sidebar.subheader("导入导出配置")

        # 导出配置
        if st.session_state.tasks or st.session_state.platforms:
            data = self.data_manager.export_data()
            json_str = json.dumps(data, indent=2, ensure_ascii=False)

            st.sidebar.download_button(
                label="导出配置为JSON",
                data=json_str,
                file_name="ai_model_config.json",
                mime="application/json"
            )

        # 导入配置
        uploaded_file = st.sidebar.file_uploader("导入JSON配置", type=["json"])
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                self.data_manager.import_data(data)
                st.sidebar.success("配置导入成功!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"导入失败: {str(e)}")


def main():
    ui = StreamlitUI()
    ui.run()


if __name__ == "__main__":
    main()