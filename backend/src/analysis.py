import math
from typing import List


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def solve(A, b):
    n = len(b)
    M = [list(map(float, A[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-10:
            M[pivot][col] += 1e-6
        M[col], M[pivot] = M[pivot], M[col]
        p = M[col][col]
        for j in range(col, n + 1):
            M[col][j] /= p
        for r in range(n):
            if r == col:
                continue
            f = M[r][col]
            for j in range(col, n + 1):
                M[r][j] -= f * M[col][j]
    return [M[i][n] for i in range(n)]

def design_matrix(rows, features):
    return [[1.0] + [float(r[f]) for f in features] for r in rows]

def regression(rows, features, target):
    X = design_matrix(rows, features)
    y = [float(r[target]) for r in rows]
    XtX = [[sum(row[i] * row[j] for row in X) for j in range(len(X[0]))] for i in range(len(X[0]))]
    Xty = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(len(X[0]))]
    beta = solve(XtX, Xty)
    pred = [sum(X[i][j] * beta[j] for j in range(len(beta))) for i in range(len(X))]
    ybar = mean(y)
    ss_tot = sum((v-ybar)**2 for v in y)
    ss_res = sum((y[i]-pred[i])**2 for i in range(len(y)))
    return {"intercept": beta[0], "coefficients": {features[i]: beta[i+1] for i in range(len(features))}, "r2": 1 - ss_res/ss_tot if ss_tot else 0, "predictions": pred}

def residuals(rows, target, controls):
    m = regression(rows, controls, target)
    X = design_matrix(rows, controls)
    return [float(rows[i][target]) - sum(X[i][j] * ([m["intercept"]] + [m["coefficients"][f] for f in controls])[j] for j in range(len(X[i]))) for i in range(len(rows))]

def pearson(a, b):
    ma, mb = mean(a), mean(b)
    da = [x-ma for x in a]
    db = [x-mb for x in b]
    den = math.sqrt(sum(x*x for x in da) * sum(y*y for y in db))
    return sum(x*y for x,y in zip(da,db))/den if den else 0.0

def partial_correlation(rows, x, y, controls):
    rx = residuals(rows, x, controls)
    ry = residuals(rows, y, controls)
    return pearson(rx, ry)

def stepwise(rows, candidates, target):
    selected = []
    remaining = list(candidates)
    base_r2 = 0.0
    steps = []
    while remaining:
        scored = []
        for f in remaining:
            result = regression(rows, selected + [f], target)
            scored.append((result["r2"], f, result))
        score, feature, result = max(scored, key=lambda x: x[0])
        gain = score - base_r2
        if gain < 0.015 and selected:
            break
        selected.append(feature)
        remaining.remove(feature)
        steps.append({"added": feature, "r2": round(score, 4), "gain": round(gain, 4)})
        base_r2 = score
        if len(selected) >= 4:
            break
    final = regression(rows, selected, target) if selected else regression(rows, [], target)
    return {"selected_features": selected, "steps": steps, "model": final}

def run_analysis(rows):
    if len(rows) < 5:
        raise ValueError("至少需要 5 份有效续租问卷")
    enriched = []
    for r in rows:
        item = dict(r)
        item["service_resolution_days"] = float(item.get("service_resolution_days") or 0)
        item["rent_burden"] = float(item.get("rent_burden") or 0)
        item["property_age_years"] = float(item.get("property_age_years") or 0)
        item["renewal_intent"] = float(item["renewal_intent"])
        enriched.append(item)
    partial = partial_correlation(enriched, "service_resolution_days", "renewal_intent", ["rent_burden", "property_age_years"])
    candidates = ["service_score", "value_score", "community_score", "cleanliness_score", "service_resolution_days", "rent_burden"]
    selected = stepwise(enriched, candidates, "renewal_intent")
    return {
        "sample_size": len(enriched),
        "partial_correlation": round(partial, 4),
        "partial_corr_label": "服务解决时长与续租意愿（控制租金压力、房龄）",
        "stepwise": {"selected_features": selected["selected_features"], "steps": selected["steps"], "coefficients": {k: round(v, 4) for k,v in selected["model"]["coefficients"].items()}, "intercept": round(selected["model"]["intercept"],4), "r2": round(selected["model"]["r2"], 4)},
        "explanation": "服务评分和解决时长进入解释模型，结果用于客户经理排序，不能替代人工沟通。" if "service_score" in selected["selected_features"] else "模型未选入服务评分，需结合访谈记录复核客户原因。"
    }
