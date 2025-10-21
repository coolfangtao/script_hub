



# ----------------- 函数2: 根据EDS数据进行分类 -----------------
def classify_inclusion(eds_data: dict, threshold: float = 0.5) -> str:
    """
    根据EDS定量分析结果和设定的优先级规则，对夹杂物进行分类。
    优先级规则: Ti/Nb > Al/Mg > La/Ce（稀土类） > Mn/S
    """
    if not eds_data:
        return "无有效数据"

    has_ti = eds_data.get('Ti', 0) > threshold or (eds_data.get('Nb', 0) > threshold)
    has_al_mg = (eds_data.get('Al', 0) > threshold) or (eds_data.get('Mg', 0) > threshold)
    has_la_ce = (eds_data.get('La', 0) > threshold) or (eds_data.get('Ce', 0) > threshold)
    has_s = (eds_data.get('Mn', 0) > threshold) or (eds_data.get('S', 0) > threshold)

    if has_ti:
        return 'Ti、Nb'
    elif has_al_mg:
        return 'Al、Mg'
    elif has_la_ce:
        return '稀土'
    elif has_s:
        return 'MnS'
    else:
        return '其他'

