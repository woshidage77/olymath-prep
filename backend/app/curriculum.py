from __future__ import annotations
from collections import Counter
from typing import Any

from .models import CurriculumCatalog, CurriculumUnit


GRADE_FIVE_UNITS: tuple[dict[str, Any], ...] = (
    {
        "id": "5a-1", "semester": "上册", "order": 1, "name": "小数乘法",
        "focus": "小数乘法、估算与购物方案",
        "olympiad_topics": ["巧算", "估算", "方案比较"],
    },
    {
        "id": "5a-2", "semester": "上册", "order": 2, "name": "位置",
        "focus": "数对、路线与坐标推理",
        "olympiad_topics": ["数对", "平移路线", "坐标推理"],
    },
    {
        "id": "5a-3", "semester": "上册", "order": 3, "name": "小数除法",
        "focus": "小数除法、周期与实际取值",
        "olympiad_topics": ["周期小数", "进一去尾", "反推数量"],
    },
    {
        "id": "5a-4", "semester": "上册", "order": 4, "name": "可能性",
        "focus": "等可能、事件比较与公平规则",
        "olympiad_topics": ["枚举", "可能性比较", "公平游戏"],
    },
    {
        "id": "5a-5", "semester": "上册", "order": 5, "name": "简易方程",
        "focus": "数量关系、列方程与验算",
        "olympiad_topics": ["年龄问题", "盈亏问题", "和差倍"],
    },
    {
        "id": "5a-6", "semester": "上册", "order": 6, "name": "多边形的面积",
        "focus": "割补、等积变形与组合图形",
        "olympiad_topics": ["割补", "等积变形", "组合面积"],
    },
    {
        "id": "5a-7", "semester": "上册", "order": 7, "name": "数学广角——植树问题",
        "focus": "间隔数、封闭路线与锯木问题",
        "olympiad_topics": ["两端植树", "封闭路线", "锯木与楼梯"],
    },
    {
        "id": "5b-1", "semester": "下册", "order": 1, "name": "观察物体（三）",
        "focus": "三视图、遮挡与立体还原",
        "olympiad_topics": ["三视图", "最少方块", "立体还原"],
    },
    {
        "id": "5b-2", "semester": "下册", "order": 2, "name": "因数与倍数",
        "focus": "整除、质数、公因数与公倍数",
        "olympiad_topics": ["整除特征", "余数问题", "公因数与公倍数"],
    },
    {
        "id": "5b-3", "semester": "下册", "order": 3, "name": "长方体和正方体",
        "focus": "展开图、表面积、体积与容积",
        "olympiad_topics": ["展开图", "表面积变化", "水位与体积"],
    },
    {
        "id": "5b-4", "semester": "下册", "order": 4, "name": "分数的意义和性质",
        "focus": "分数意义、约分、通分与互化",
        "olympiad_topics": ["单位一", "分数性质", "公因数与通分"],
    },
    {
        "id": "5b-5", "semester": "下册", "order": 5, "name": "图形的运动（三）",
        "focus": "旋转、平移与拼图",
        "olympiad_topics": ["旋转中心", "轨迹", "拼图变换"],
    },
    {
        "id": "5b-6", "semester": "下册", "order": 6, "name": "分数的加法和减法",
        "focus": "异分母运算、混合运算与实际问题",
        "olympiad_topics": ["巧算", "分数应用", "通知问题"],
    },
    {
        "id": "5b-7", "semester": "下册", "order": 7, "name": "折线统计图",
        "focus": "变化趋势、双线比较与数据判断",
        "olympiad_topics": ["趋势判断", "数据反推", "复式折线图"],
    },
    {
        "id": "5b-8", "semester": "下册", "order": 8, "name": "数学广角——找次品",
        "focus": "天平称量、分组与最坏情况",
        "olympiad_topics": ["三分法", "信息量", "最少次数"],
    },
)

UNIT_BY_ID = {unit["id"]: unit for unit in GRADE_FIVE_UNITS}


def unit_metadata(unit_id: str) -> dict[str, Any]:
    return UNIT_BY_ID[unit_id]


def build_curriculum_catalog(grade: int, topic_counts: Counter[str]) -> CurriculumCatalog:
    if grade != 5:
        return CurriculumCatalog(
            grade=grade,
            edition="人教版单元框架",
            available=False,
            units=[],
        )
    units = [
        CurriculumUnit(
            **unit,
            grade=5,
            problem_count=topic_counts[unit["name"]],
        )
        for unit in GRADE_FIVE_UNITS
    ]
    return CurriculumCatalog(
        grade=5,
        edition="人教版五年级数学单元框架",
        available=True,
        units=units,
    )
