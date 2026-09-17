from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .curriculum import GRADE_FIVE_UNITS, unit_metadata
from .demo_data import DEMO_PROBLEMS


UNIT_TEACHING: dict[str, dict[str, list[str] | str]] = {
    "5a-1": {"concepts": ["小数乘法", "估算"], "methods": ["先估后算", "数量关系"], "tags": ["计算", "应用"]},
    "5a-2": {"concepts": ["数对", "位置"], "methods": ["先列后行", "坐标表示"], "tags": ["坐标", "推理"]},
    "5a-3": {"concepts": ["小数除法", "商"], "methods": ["单位分析", "进一去尾"], "tags": ["计算", "应用"]},
    "5a-4": {"concepts": ["可能性", "等可能"], "methods": ["分类枚举", "比较数量"], "tags": ["概率", "枚举"]},
    "5a-5": {"concepts": ["未知数", "数量关系"], "methods": ["设未知数", "列方程验算"], "tags": ["方程", "应用"]},
    "5a-6": {"concepts": ["多边形面积", "等积"], "methods": ["割补", "画辅助线"], "tags": ["几何", "面积"]},
    "5a-7": {"concepts": ["间隔数", "端点"], "methods": ["画线段图", "点段对应"], "tags": ["植树问题", "规律"]},
    "5b-1": {"concepts": ["三视图", "投影"], "methods": ["固定视角", "逐列观察"], "tags": ["空间想象", "几何"]},
    "5b-2": {"concepts": ["因数", "倍数"], "methods": ["列举", "整除分析"], "tags": ["数论", "规律"]},
    "5b-3": {"concepts": ["长方体", "体积"], "methods": ["展开分析", "单位一致"], "tags": ["立体几何", "测量"]},
    "5b-4": {"concepts": ["分数意义", "分数性质"], "methods": ["确定单位一", "约分通分"], "tags": ["分数", "数感"]},
    "5b-5": {"concepts": ["旋转", "平移"], "methods": ["找旋转中心", "追踪关键点"], "tags": ["图形运动", "几何"]},
    "5b-6": {"concepts": ["分数加减", "通分"], "methods": ["统一分数单位", "分步计算"], "tags": ["分数", "应用"]},
    "5b-7": {"concepts": ["折线统计图", "变化趋势"], "methods": ["读点", "比较变化量"], "tags": ["统计", "数据"]},
    "5b-8": {"concepts": ["找次品", "最坏情况"], "methods": ["尽量三等分", "分类讨论"], "tags": ["逻辑", "称量"]},
}


UNIT_SHORT_TITLES: dict[str, str] = {
    "5a-1": "小数乘法",
    "5a-2": "坐标定位",
    "5a-3": "小数除法",
    "5a-4": "概率比较",
    "5a-5": "方程求解",
    "5a-6": "图形面积",
    "5a-7": "间隔计数",
    "5b-1": "立体观察",
    "5b-2": "因倍判定",
    "5b-3": "体积计算",
    "5b-4": "分数性质",
    "5b-5": "旋转变换",
    "5b-6": "分数运算",
    "5b-7": "趋势判断",
    "5b-8": "称量推理",
}


SHORT_TITLE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("3年前",), "年龄和差"),
    (("岁数的5倍",), "年龄倍数"),
    (("鸡兔同笼",), "鸡兔同笼"),
    (("面包车", "中巴客车"), "车辆分组"),
    (("桃树", "梨树"), "果树倍数"),
    (("3人一组", "5人一组"), "分组倍数"),
    (("零件", "加工"), "工效方程"),
    (("油菜籽", "榨出"), "榨油比率"),
    (("每页排",), "排版计数"),
    (("小船租金",), "租船计费"),
    (("电话线杆",), "线杆间隔"),
    (("次品", "天平", "偏轻", "偏重", "质量不同"), "称量推理"),
    (("电话", "通知"), "电话通知"),
    (("植树", "树苗", "棵树"), "间隔植树"),
    (("电线杆", "路灯", "灯笼"), "间隔设点"),
    (("锯", "截成"), "锯木计数"),
    (("台阶", "楼梯", "几楼"), "楼梯计数"),
    (("年龄", "今年", "几岁", "岁"), "年龄推理"),
    (("每人出", "多出", "少了"), "盈亏问题"),
    (("速度", "路程", "迟到", "提前"), "行程问题"),
    (("水位", "浸没"), "水位变化"),
    (("鱼缸", "水槽", "水池"), "水池容积"),
    (("仓库", "沙坑"), "容积计算"),
    (("长方体", "正方体", "棱长"), "立体计算"),
    (("展开图", "表面积", "纸盒"), "展开表面"),
    (("梯形",), "梯形面积"),
    (("三角形",), "三角面积"),
    (("平行四边形",), "平行面积"),
    (("正方形",), "正方计算"),
    (("长方形",), "矩形计算"),
    (("周长",), "周长计算"),
    (("面积",), "面积计算"),
    (("数对", "坐标"), "坐标定位"),
    (("随机", "可能性", "摸球", "转盘"), "概率比较"),
    (("旋转", "平移", "顺时针", "逆时针"), "旋转变换"),
    (("公因数", "最大公因数"), "公因数法"),
    (("公倍数", "最小公倍数"), "公倍数法"),
    (("因数", "倍数", "质数", "整除"), "因倍判定"),
    (("分子", "分母", "约分", "通分"), "分数性质"),
    (("几分之几", "还剩"), "分数应用"),
    (("平均",), "平均问题"),
    (("循环小数",), "循环小数"),
    (("每人", "人数"), "人数推理"),
)


TITLE_UNIT_LIMITS: dict[str, set[str]] = {
    "称量推理": {"5b-8"},
    "电话通知": {"5a-7"},
    "间隔植树": {"5a-7"},
    "间隔设点": {"5a-7"},
    "锯木计数": {"5a-7"},
    "楼梯计数": {"5a-7"},
    "线杆间隔": {"5a-7"},
    "年龄推理": {"5a-5"},
    "年龄和差": {"5a-5"},
    "年龄倍数": {"5a-5"},
    "盈亏问题": {"5a-5"},
    "行程问题": {"5a-5"},
    "人数推理": {"5a-5"},
    "鸡兔同笼": {"5a-5"},
    "果树倍数": {"5a-5"},
    "工效方程": {"5a-5"},
    "车辆分组": {"5b-2"},
    "分组倍数": {"5b-2"},
    "水位变化": {"5b-3"},
    "水池容积": {"5b-3"},
    "容积计算": {"5b-3"},
    "立体计算": {"5b-3"},
    "展开表面": {"5b-3"},
    "梯形面积": {"5a-6"},
    "三角面积": {"5a-6"},
    "平行面积": {"5a-6"},
    "正方计算": {"5a-6"},
    "矩形计算": {"5a-6"},
    "周长计算": {"5a-6"},
    "面积计算": {"5a-6"},
    "坐标定位": {"5a-2"},
    "概率比较": {"5a-4"},
    "旋转变换": {"5b-5"},
    "公因数法": {"5b-2"},
    "公倍数法": {"5b-2"},
    "因倍判定": {"5b-2"},
    "分数性质": {"5b-4"},
    "分数应用": {"5b-4", "5b-6"},
    "平均问题": {"5a-3"},
    "循环小数": {"5a-3"},
    "榨油比率": {"5a-3"},
    "排版计数": {"5a-3"},
    "租船计费": {"5a-3"},
}


ORIGINAL_SEEDS: tuple[tuple[str, str, str, str], ...] = (
    ("5a-1", "单价与重量", "苹果每千克12.8元，买2.5千克。先估一估，再计算应付多少元。", "32元"),
    ("5a-1", "购物方案巧算", "4支笔每支2.75元，3本本子每本6.4元。怎样计算更容易检查？", "30.2元"),
    ("5a-2", "数对移动", "棋子从(3,2)先向右移动4格，再向上移动3格，最后的位置用数对怎样表示？", "(7,5)"),
    ("5a-2", "补全长方形顶点", "长方形三个顶点是(1,1)、(1,4)、(6,1)，第四个顶点在哪里？", "(6,4)"),
    ("5a-3", "装瓶要进一", "7.5升果汁装入每瓶0.6升的瓶子，至少需要多少个瓶子？", "13个"),
    ("5a-3", "循环小数找数位", "1÷6写成循环小数后，小数点后第20位是几？", "6"),
    ("5a-4", "摸球比较", "袋中有3个红球、2个蓝球、1个黄球，任意摸一个，三种颜色出现的可能性怎样比较？", "红球最大，蓝球其次，黄球最小"),
    ("5a-4", "转盘规则是否公平", "转盘均分为1至8八个数字。甲转到偶数得1分，乙转到奇数得1分，这个规则公平吗？", "公平，各有4个等可能结果"),
    ("5a-5", "年龄关系", "爸爸今年38岁，比小明年龄的3倍多2岁。小明今年多少岁？", "12岁"),
    ("5a-5", "盈亏问题", "同学合买礼物，每人出8元多4元，每人出7元少5元。共有多少人？", "9人"),
    ("5a-6", "梯形面积", "一个梯形上底6厘米、下底10厘米、高5厘米，面积是多少？", "40平方厘米"),
    ("5a-6", "等积变形", "平行四边形底12厘米、高7厘米，剪拼成长方形后面积是否改变？面积是多少？", "不变，84平方厘米"),
    ("5a-7", "两端都栽", "一条240米的小路，每隔15米栽一棵树，两端都栽，一共栽多少棵？", "17棵"),
    ("5a-7", "封闭路线", "圆形跑道一周360米，每隔12米设置一个标志，需设置多少个？", "30个"),
    ("5b-2", "最大分组数", "36支铅笔和48块橡皮平均分给若干组，每组两种物品数量相同且没有剩余，最多分几组？", "12组"),
    ("5b-2", "公倍数筛选", "30到50之间，同时是6和8的倍数的数是多少？", "48"),
    ("5b-3", "无盖鱼缸表面积", "无盖长方体鱼缸长8分米、宽5分米、高4分米，制作它至少需要多少平方分米玻璃？", "144平方分米"),
    ("5b-3", "水位上升", "底面积60平方厘米的水槽放入一个体积180立方厘米的物体，物体完全浸没，水面上升多少厘米？", "3厘米"),
    ("5b-4", "分数基本性质", "把3/5的分子加上6，要使分数大小不变，分母应加上多少？", "10"),
    ("5b-4", "单位一判断", "一根绳子先用去全长的2/5，再用去剩下的1/3。第二次用去全长的几分之几？", "1/5"),
    ("5b-5", "关键点旋转", "点A(4,2)绕点O(2,2)逆时针旋转90度后，A点在哪里？", "(2,4)"),
    ("5b-5", "旋转后的不变量", "一个正方形绕中心旋转90度，哪些量没有改变？", "边长、周长、面积和形状均不变"),
    ("5b-6", "异分母相加", "一项工程上午完成2/3，下午完成1/4，一共完成全工程的几分之几？", "11/12"),
    ("5b-6", "连续减去两部分", "一桶油先用去3/8，又用去1/6，还剩几分之几？", "11/24"),
    ("5b-7", "读取最大增量", "某地周一至周五气温依次为18、20、19、24、23摄氏度，哪两天之间升温最多？", "周三到周四，升高5摄氏度"),
    ("5b-7", "比较两条变化线", "甲组成绩从70升到86，乙组从78升到88。哪组提高更多？多提高多少分？", "甲组，多提高6分"),
    ("5b-8", "九枚硬币找轻币", "9枚外观相同的硬币中有1枚较轻，用无砝码天平至少称几次能保证找出？", "2次"),
    ("5b-8", "二十七枚找重币", "27枚外观相同的棋子中有1枚较重，用无砝码天平至少称几次能保证找出？", "3次"),
)


def _original_problem(index: int, seed: tuple[str, str, str, str]) -> dict[str, Any]:
    unit_id, title, statement, answer = seed
    unit = unit_metadata(unit_id)
    teaching = UNIT_TEACHING[unit_id]
    problem_id = f"topic-seed-{index:03d}"
    return {
        "id": problem_id,
        "revision_id": f"{problem_id}-r1",
        "title": title,
        "statement": statement,
        "question": "请先说出数量关系或图形关系，再完成解答。",
        "answer": answer,
        "teaching_role": "专题例题",
        "difficulty": "进阶",
        "source_label": "一朵教学原创题",
        "source_status": "原创待教师审核",
        "school_stage": "小学",
        "grade": 5,
        "topic": unit["name"],
        "semester": unit["semester"],
        "unit_id": unit_id,
        "unit_name": unit["name"],
        "content_kind": "原创教学题",
        "has_interactive_model": False,
        "concepts": list(teaching["concepts"]),
        "methods": list(teaching["methods"]),
        "tags": list(teaching["tags"]),
        "purpose": f"从题目条件中提炼{unit['focus']}，让学生说明每一步为什么成立。",
        "teacher_prompt": "先不计算：题目给了什么、要求什么、两者怎样联系？",
        "teaching_note": "让学生先用图、表或算式表达关系，再比较不同方法并回到题目验算。",
        "cubes": [],
        "next": None,
    }


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _classify_cmath(text: str) -> str:
    if _contains_any(text, ("面包车", "中巴客车")):
        return "5b-2"
    if "合唱队" in text and "余" in text:
        return "5b-2"
    if _contains_any(text, ("3人一组", "5人一组")):
        return "5b-2"
    if _contains_any(text, ("每人栽", "每人各栽")):
        return "5a-5"
    if _contains_any(text, ("平均", "油菜籽", "榨出", "每页排", "小船租金")):
        return "5a-3"
    if _contains_any(text, ("次品", "天平", "不一样重", "偏轻", "偏重", "质量不同")):
        return "5b-8"
    if _contains_any(text, ("长方体", "正方体", "体积", "容积", "水位", "纸盒", "棱长", "木料", "木块", "立方米", "沙坑", "蓄水池")):
        return "5b-3"
    if _contains_any(text, ("旋转", "平移", "顺时针", "逆时针")):
        return "5b-5"
    if _contains_any(text, ("统计图", "气温", "折线", "增长趋势", "下降趋势")):
        return "5b-7"
    if _contains_any(text, ("植树", "电线杆", "路灯", "间隔", "每隔", "锯", "台阶", "楼梯", "树苗", "棵树", "垃圾桶", "相邻的两个同学", "敲", "电话线杆")):
        return "5a-7"
    if _contains_any(text, ("三角形", "平行四边形", "梯形", "面积", "周长", "长方形", "正方形")):
        return "5a-6"
    if _contains_any(text, ("数对", "坐标", "第几根", "第几层", "位置")):
        return "5a-2"
    if _contains_any(text, ("随机", "可能性", "摸球", "转盘")):
        return "5a-4"
    if _contains_any(text, ("通知", "电话")):
        return "5a-7"
    fractions = re.findall(r"\d+/\d+", text)
    if len(fractions) >= 2 or _contains_any(text, ("一共用了几分之几", "还剩几分之几")):
        return "5b-6"
    if fractions or _contains_any(text, ("几分之几", "分子", "分母", "约分", "通分")):
        return "5b-4"
    if _contains_any(text, ("因数", "倍数", "质数", "合数", "公因数", "公倍数", "整除", "余数", "同时")):
        return "5b-2"
    if _contains_any(text, ("年龄", "今年", "几岁", "岁", "提前", "原计划", "每人出", "多出", "少了")):
        return "5a-5"
    if re.search(r"\d+\.\d+", text):
        if _contains_any(text, ("平均", "每", "需要", "可以", "装")):
            return "5a-3"
        return "5a-1"
    return "5a-5"


def _short_title(text: str, unit_id: str) -> str:
    normalized = re.sub(r"\s+", "", text)
    for keywords, title in SHORT_TITLE_RULES:
        allowed_units = TITLE_UNIT_LIMITS.get(title)
        if allowed_units is not None and unit_id not in allowed_units:
            continue
        if _contains_any(normalized, keywords):
            return title
    return UNIT_SHORT_TITLES[unit_id]


def _load_cmath_problems() -> list[dict[str, Any]]:
    data_path = Path(__file__).resolve().parents[1] / "data" / "cmath_grade5_cc_by_4.jsonl"
    rows = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    problems: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        unit_id = _classify_cmath(row["input"])
        unit = unit_metadata(unit_id)
        teaching = UNIT_TEACHING[unit_id]
        problem_id = f"cmath-g5-{index:03d}"
        reasoning_steps = int(row.get("reasoning_step", 1))
        problems.append({
            "id": problem_id,
            "revision_id": f"{problem_id}-upstream-2023",
            "title": _short_title(row["input"], unit_id),
            "statement": row["input"],
            "question": "请列出关键数量关系并完成解答。",
            "answer": str(row["golden"]),
            "teaching_role": "题库练习",
            "difficulty": "基础" if reasoning_steps <= 1 else "进阶" if reasoning_steps <= 2 else "挑战",
            "source_label": "CMATH 五年级开放数据",
            "source_status": "CC BY 4.0 · 待教师分级",
            "school_stage": "小学",
            "grade": 5,
            "topic": unit["name"],
            "semester": unit["semester"],
            "unit_id": unit_id,
            "unit_name": unit["name"],
            "content_kind": "开放数据题",
            "has_interactive_model": False,
            "concepts": list(teaching["concepts"]),
            "methods": list(teaching["methods"]),
            "tags": [*teaching["tags"], "CMATH"],
            "purpose": f"练习{unit['focus']}，重点观察学生如何把文字条件转成数量关系。",
            "teacher_prompt": "先圈出有用条件，再说出第一步为什么这样列式。",
            "teaching_note": "数据集只提供标准答案。课堂使用前，教师需要补充分步解法并复核专题归类。",
            "cubes": [],
            "next": None,
        })
    return problems


def _enrich_cube_problems() -> None:
    unit = unit_metadata("5b-1")
    for problem in DEMO_PROBLEMS:
        problem.update({
            "semester": unit["semester"],
            "unit_id": unit["id"],
            "unit_name": unit["name"],
            "content_kind": "原创教学题",
            "has_interactive_model": True,
            "topic": unit["name"],
        })


_enrich_cube_problems()
ORIGINAL_TOPIC_PROBLEMS = [
    _original_problem(index, seed)
    for index, seed in enumerate(ORIGINAL_SEEDS, start=1)
]
CMATH_PROBLEMS = _load_cmath_problems()
ALL_PROBLEMS = [*DEMO_PROBLEMS, *ORIGINAL_TOPIC_PROBLEMS, *CMATH_PROBLEMS]


def _mark_featured_problems() -> None:
    featured_units: set[str] = set()
    for problem in ALL_PROBLEMS:
        problem["is_featured"] = False
        if problem["content_kind"] != "原创教学题":
            continue
        if problem["unit_id"] in featured_units:
            continue
        problem["is_featured"] = True
        problem["difficulty"] = "基础"
        problem["teaching_role"] = "推荐起点"
        featured_units.add(problem["unit_id"])


_mark_featured_problems()
