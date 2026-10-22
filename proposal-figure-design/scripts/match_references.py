#!/usr/bin/env python3
"""Rank paired reference Markdown/PNG files against a content specification."""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from pathlib import Path


KEYWORDS = (
    "技术架构", "系统架构", "研究内容", "研究基础", "团队基础", "研究方案",
    "技术路线", "科学问题", "关键科学问题", "创新点", "目标", "指标",
    "平台", "数据", "多模态", "智能体", "机制", "闭环", "流程", "输入",
    "输出", "场景", "应用", "验证", "成果", "论文", "专利", "奖项", "照片",
    "三层", "四象限", "左右", "上下", "并列", "递进", "辐射", "中心", "矩阵",
)


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def char_ngrams(text: str, sizes: tuple[int, ...] = (2, 3)) -> Counter[str]:
    clean = normalized_text(text)
    return Counter(
        clean[i : i + size]
        for size in sizes
        for i in range(max(0, len(clean) - size + 1))
        if re.search(r"[\u4e00-\u9fffA-Za-z0-9]", clean[i : i + size])
    )


def cosine(left: Counter[str], right: Counter[str]) -> float:
    common = left.keys() & right.keys()
    numerator = sum(left[k] * right[k] for k in common)
    left_norm = math.sqrt(sum(v * v for v in left.values()))
    right_norm = math.sqrt(sum(v * v for v in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def matched_keywords(query: str, candidate: str) -> list[str]:
    return [term for term in KEYWORDS if term in query and term in candidate]


def rank(query_text: str, references: Path) -> list[dict[str, object]]:
    query_norm = normalized_text(query_text)
    query_grams = char_ngrams(query_text)
    results: list[dict[str, object]] = []

    for md_path in sorted(references.glob("*.md")):
        png_path = md_path.with_suffix(".png")
        if not png_path.exists():
            continue
        candidate_text = md_path.read_text(encoding="utf-8")
        candidate_norm = normalized_text(candidate_text)
        shared = matched_keywords(query_norm, candidate_norm)
        semantic = cosine(query_grams, char_ngrams(candidate_text))
        keyword_score = min(len(shared) / 8.0, 1.0)
        score = 0.7 * semantic + 0.3 * keyword_score
        results.append(
            {
                "stem": md_path.stem,
                "md": md_path,
                "png": png_path,
                "score": score,
                "semantic": semantic,
                "shared": shared,
            }
        )

    return sorted(results, key=lambda item: (-float(item["score"]), str(item["stem"])))


def render(query_path: Path, ranked: list[dict[str, object]], top_k: int) -> str:
    lines = [
        "# 参考图匹配与选择",
        "",
        f"- 查询内容：`{query_path.resolve()}`",
        "- 说明：分数用于缩小候选范围，最终选择必须同时阅读 Markdown 并查看 PNG。",
        "",
        "## 候选排名",
        "",
    ]
    for index, item in enumerate(ranked[:top_k], start=1):
        shared = "、".join(item["shared"]) if item["shared"] else "未命中预设主题词"
        lines.extend(
            [
                f"### {index}. {item['stem']}（综合分 {float(item['score']):.3f}）",
                "",
                f"- 参考 Markdown：`{Path(item['md']).resolve()}`",
                f"- 参考图片：`{Path(item['png']).resolve()}`",
                f"- 字符语义相似度：{float(item['semantic']):.3f}",
                f"- 共同主题词：{shared}",
                "- 人工判断：待填写",
                "",
            ]
        )
    lines.extend(
        [
            "## 主参考",
            "",
            "- 参考 Markdown：",
            "- 参考图片：",
            "- 角色：布局参考 / 风格参考 / 局部组件参考",
            "- 内容语义匹配原因：",
            "- 借用的视觉规律：",
            "- 必须舍弃的元素：",
            "",
            "## 辅参考（最多 2 个）",
            "",
            "## 无高匹配参考说明",
            "",
            "不适用时删除本节；适用时说明为何从零设计。",
            "",
            "## 选择门",
            "",
            "- [ ] 已同时阅读参考 Markdown 和查看对应 PNG",
            "- [ ] 主参考只有 1 个",
            "- [ ] 辅参考不超过 2 个",
            "- [ ] 已明确每张图的参考角色",
            "- [ ] 不会复制参考图中的项目事实、文字或数字",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("content_md", type=Path)
    parser.add_argument("--references", type=Path, default=Path("references"))
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if not args.content_md.is_file():
        parser.error(f"content Markdown not found: {args.content_md}")
    if not args.references.is_dir():
        parser.error(f"references directory not found: {args.references}")
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    query_text = args.content_md.read_text(encoding="utf-8")
    ranked = rank(query_text, args.references)
    if not ranked:
        parser.error("no paired .md/.png references found")

    output = render(args.content_md, ranked, args.top_k)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
