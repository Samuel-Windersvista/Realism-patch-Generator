#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from typing import Dict, Iterable, List, Sequence, Tuple

import tkinter as tk
from tkinter import messagebox, ttk


RangeTuple = Tuple[float | int, float | int]


@dataclass(frozen=True)
class AssignmentSpec:
    file_name: str
    assignment_name: str
    label: str


@dataclass
class RangeEntry:
    file_name: str
    assignment_name: str
    assignment_label: str
    path: Tuple[str, ...]
    profile: str
    field: str
    value: RangeTuple
    original_value: RangeTuple
    type_hints: Tuple[type, type]

    @property
    def is_dirty(self) -> bool:
        return self.value != self.original_value


@dataclass(frozen=True)
class SaveResult:
    changed_count: int
    backup_dir: Path | None


RULE_SPECS: Sequence[AssignmentSpec] = (
    AssignmentSpec("weapon_rule_ranges.py", "WEAPON_PROFILE_RANGES", "武器基础规则"),
    AssignmentSpec("weapon_refinement_rules.py", "WEAPON_CALIBER_RULE_MODIFIERS", "武器口径精修"),
    AssignmentSpec("weapon_refinement_rules.py", "WEAPON_STOCK_RULE_MODIFIERS", "武器枪托精修"),
    AssignmentSpec("attachment_rule_ranges.py", "MOD_PROFILE_RANGES", "附件规则"),
    AssignmentSpec("gear_rule_ranges.py", "GEAR_PROFILE_RANGES", "装备规则"),
    AssignmentSpec("ammo_rule_ranges.py", "AMMO_PROFILE_RANGES", "弹药基础规则"),
    AssignmentSpec("ammo_rule_ranges.py", "AMMO_SPECIAL_MODIFIERS", "弹药弹种修正"),
    AssignmentSpec("ammo_rule_ranges.py", "AMMO_PENETRATION_TIERS", "弹药穿深档位"),
    AssignmentSpec("ammo_rule_ranges.py", "AMMO_PENETRATION_MODIFIERS", "弹药穿深修正"),
)


FIELD_EXPLANATIONS: Dict[str, str] = {
    "Accuracy": "精度修正。更高通常表示弹着更集中、远距离表现更稳。",
    "AimSpeed": "举枪/开镜速度相关修正。更高通常表示抬枪更快，小于 0 往往表示操作变慢。",
    "AimStability": "瞄准稳定性。更高通常表示镜内晃动更小、持续瞄准更轻松。",
    "AmmoDamage": "弹药伤害，通常越高越偏向肉伤输出。",
    "ArmorDamage": "对护甲或插板耐久的损耗倍率。更高通常表示更容易打废护具。",
    "AutoROF": "全自动射速。更高代表每分钟发射数更多。",
    "BallisticCoeficient": "弹道系数。更高通常表示远距离掉速更慢、保速更好。",
    "BaseChamberCheckSpeed": "基础验膛速度倍率。更高表示验膛动作更快。",
    "BaseChamberSpeedMulti": "基础上膛速度倍率。更高表示拉机柄/上膛更快。",
    "BaseFixSpeed": "基础排障速度倍率。更高表示处理故障更快。",
    "BaseReloadSpeedMulti": "基础换弹速度倍率。更高表示整枪换弹更利索。",
    "BaseTorque": "基础扭矩/操控阻力。通常越低越灵活，越高越沉重。",
    "BulletMassGram": "弹头质量。更高通常后坐更重、保动能更强。",
    "CameraRecoil": "镜头后坐/视角冲击。更高通常画面更抖，负值修正常用于压低视觉后坐。",
    "CheckTimeModifier": "检查动作修正，常见于弹匣检查或部件检查。更高表示动作更慢。",
    "Comfort": "穿戴舒适度或负载友好度。更高通常表示负担更轻、长时间使用更舒服。",
    "Convergence": "后坐收束能力。更高通常表示连发后更容易回正到瞄准线附近。",
    "CoolFactor": "散热效率。更高通常表示降温更快、热量更容易压住。",
    "Damage": "伤害值。更高通常代表单发肉伤更强。",
    "dB": "耳机增益或声音放大能力。更高通常表示环境声音更明显。",
    "Dispersion": "散布/离散程度。对武器通常越低越稳，对附件修正常看作散布影响。",
    "DurabilityBurnModificator": "耐久燃烧倍率。更高通常表示更伤枪、更耗武器耐久。",
    "Ergonomics": "人机工效。更高通常代表举枪、转枪、操作和持枪体验更轻快。",
    "Flash": "枪口焰或闪光影响。更低通常更利于压火光，更高则更显眼。",
    "GasProtection": "气体防护能力。更高通常表示防毒面具或相关装备更能抗毒气。",
    "Handling": "综合操控感修正。更高通常表示切枪、转枪、姿态调整更顺手。",
    "HeatFactor": "发热强度。更高通常表示连续使用时更容易积热。",
    "HeavyBleedingDelta": "重出血倾向修正。更高通常表示更容易造成重出血。",
    "HipInnaccuracyGain": "腰射失准累积速度。更高通常表示连续腰射更容易飘。",
    "HipAccuracyRestorationSpeed": "腰射精度恢复速度。更高通常表示停止射击后恢复更快。",
    "HorizontalRecoil": "水平后坐。通常越低越稳定，越高越容易左右摆动。",
    "InitialSpeed": "初速。更高通常表示飞行时间更短、弹道更平直。",
    "LightBleedingDelta": "轻出血倾向修正。更高通常表示更容易造成轻出血。",
    "LoadUnloadModifier": "装填/退弹修正。更高通常表示压弹、退弹等动作更慢。",
    "Loudness": "响度。更低通常更安静，更高表示开火或部件声音更明显。",
    "MalfFeedChance": "供弹故障概率。更高通常表示更容易发生卡弹或供弹异常。",
    "MalfMisfireChance": "哑火故障概率。更高通常表示更容易击发失败。",
    "MinChamberSpeed": "上膛最小速度边界。更高通常表示动作下限更快。",
    "MisfireChance": "失火/哑火概率。更高通常表示弹药或武器更不稳定。",
    "ModMalfunctionChance": "附件导致的故障概率修正。更高通常表示更容易引入可靠性问题。",
    "OffsetRotation": "后坐或持枪偏移角。更高通常表示姿态偏转更明显。",
    "PenetrationPower": "穿深数值。更高通常越容易穿透更高等级护甲。",
    "RadProtection": "辐射防护能力。更高通常表示更抗辐射环境。",
    "RecoilAngle": "后坐方向角。偏离过大可能导致后坐方向异常。",
    "RecoilDamping": "后坐阻尼。更高通常表示后坐衰减更快、枪更容易稳住。",
    "RecoilHandDamping": "手部后坐阻尼。更高通常表示操作者对后坐的吸收更明显。",
    "RecoilIntensity": "程序化后坐强度。更高通常代表连续射击时整体推动感更强。",
    "ReloadSpeed": "换弹相关修正。更高通常表示动作更快，负值常表示拖慢。",
    "ReloadSpeedMulti": "换弹速度倍率。大于 1 常表示更快，小于 1 则更慢。",
    "SemiROF": "半自动射速上限。更高通常表示点射节奏更快。",
    "ShotgunDispersion": "霰弹散布。更高通常弹丸铺得更开。",
    "SpallReduction": "破片或飞溅伤害抑制能力。当前规则里数值越低通常越能压制二次破片影响。",
    "speedPenaltyPercent": "移速惩罚百分比。数值越负通常说明装备越拖慢移动。",
    "Velocity": "速度修正。武器中常指枪口初速修正，附件里常表示对弹速的影响。",
    "VerticalRecoil": "垂直后坐。通常越低越容易压枪，越高越容易枪口上跳。",
    "VisualMulti": "视觉后坐倍率。更高通常画面冲击感更强、更跳屏。",
    "weaponErgonomicPenalty": "装备对武器操控的人机惩罚。越负通常表示举枪和转枪体验越差。",
    "Weight": "重量。更高通常意味着负担更大，也可能影响手感与机动。",
}


ASSIGNMENT_EXPLANATIONS: Dict[str, str] = {
    "WEAPON_PROFILE_RANGES": "这是武器基础区间，生成器会把武器核心属性采样到这个范围内。",
    "WEAPON_CALIBER_RULE_MODIFIERS": "这是口径精修增量，正负值会在武器基础区间之上叠加，用来拉开不同口径的手感差异。",
    "WEAPON_STOCK_RULE_MODIFIERS": "这是枪托形态精修增量，主要用于区分固定托、折叠托、无托和 bullpup 的后坐与操控差异。",
    "MOD_PROFILE_RANGES": "这是附件档位范围；大多数值是附件对宿主武器的修正，负值不一定是坏事，要结合字段含义看。",
    "GEAR_PROFILE_RANGES": "这是装备范围，主要影响舒适度、破片抑制、换弹倍率和机动惩罚。",
    "AMMO_PROFILE_RANGES": "这是弹药基础区间，决定每种口径的大致伤害、穿深、热量和故障风险基线。",
    "AMMO_SPECIAL_MODIFIERS": "这是弹种型号修正，会在基础口径区间上进一步叠加，用来区分 AP、曳光、空尖等弹种。",
    "AMMO_PENETRATION_TIERS": "这是穿深分层定义，用于把具体穿深值归类到不同档位。",
    "AMMO_PENETRATION_MODIFIERS": "这是穿深档位修正，命中某个穿深层后会对伤害、热量、故障率等字段再做增量调整。",
}


TREND_HINTS: Dict[str, str] = {
    "VerticalRecoil": "武器基础值里通常越低越稳；附件/精修增量里负值通常表示减后坐，正值表示加后坐。",
    "HorizontalRecoil": "武器基础值里通常越低越稳；附件/精修增量里负值通常表示减横摆。",
    "CameraRecoil": "通常越低越不晃；增量规则里负值多半是在压视觉后坐。",
    "Ergonomics": "通常越高越顺手；若是装备惩罚语义则需要结合字段名称一起看。",
    "Convergence": "通常越高越容易回正。",
    "Dispersion": "通常越低越集中。",
    "VisualMulti": "通常越低视觉冲击越小，越高越跳屏。",
    "PenetrationPower": "通常越高越容易穿甲，但也往往伴随更多代价。",
    "Damage": "通常越高肉伤越强。",
    "SpallReduction": "当前 gear 规则里通常越低越能减少二次破片影响。",
    "ReloadSpeedMulti": "大于 1 偏快，小于 1 偏慢。",
    "Comfort": "通常越高越轻松。",
    "speedPenaltyPercent": "越负通常越拖慢移动。",
    "weaponErgonomicPenalty": "越负通常对持枪手感越不友好。",
}


def _line_offsets(text: str) -> List[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _position_to_offset(offsets: Sequence[int], lineno: int, col_offset: int) -> int:
    return offsets[lineno - 1] + col_offset


def _literal_number(node: ast.AST) -> float | int:
    value = ast.literal_eval(node)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("节点不是数值")
    return value


class RuleFileParser:
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def parse_entries(self, assignment_name: str, label: str) -> List[RangeEntry]:
        text = self.file_path.read_text(encoding="utf-8")
        module = ast.parse(text)
        assignment = self._find_assignment(module, assignment_name)
        if assignment is None:
            raise KeyError(f"未找到变量 {assignment_name}")
        if assignment.value is None:
            raise ValueError(f"变量 {assignment_name} 没有可解析的值")

        entries: List[RangeEntry] = []
        self._collect_range_entries(
            file_name=self.file_path.name,
            assignment_name=assignment_name,
            assignment_label=label,
            node=assignment.value,
            path=(assignment_name,),
            entries=entries,
        )
        return entries

    def build_replacements(
        self,
        assignment_name: str,
        updates: Dict[Tuple[str, ...], RangeEntry],
    ) -> List[Tuple[int, int, str]]:
        text = self.file_path.read_text(encoding="utf-8")
        offsets = _line_offsets(text)
        module = ast.parse(text)
        assignment = self._find_assignment(module, assignment_name)
        if assignment is None:
            raise KeyError(f"未找到变量 {assignment_name}")
        if assignment.value is None:
            raise ValueError(f"变量 {assignment_name} 没有可解析的值")

        replacements: List[Tuple[int, int, str]] = []
        self._collect_replacements(
            node=assignment.value,
            path=(assignment_name,),
            offsets=offsets,
            updates=updates,
            replacements=replacements,
        )
        return replacements

    @staticmethod
    def _find_assignment(module: ast.Module, assignment_name: str) -> ast.Assign | ast.AnnAssign | None:
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == assignment_name:
                        return node
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == assignment_name:
                return node
        return None

    def _collect_range_entries(
        self,
        file_name: str,
        assignment_name: str,
        assignment_label: str,
        node: ast.AST,
        path: Tuple[str, ...],
        entries: List[RangeEntry],
    ) -> None:
        if isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                if key_node is None:
                    continue
                key = ast.literal_eval(key_node)
                if not isinstance(key, str):
                    continue
                self._collect_range_entries(
                    file_name=file_name,
                    assignment_name=assignment_name,
                    assignment_label=assignment_label,
                    node=value_node,
                    path=path + (key,),
                    entries=entries,
                )
            return

        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            try:
                min_value = _literal_number(node.elts[0])
                max_value = _literal_number(node.elts[1])
            except (ValueError, TypeError):
                return

            profile, field = self._split_path(path)
            entries.append(
                RangeEntry(
                    file_name=file_name,
                    assignment_name=assignment_name,
                    assignment_label=assignment_label,
                    path=path,
                    profile=profile,
                    field=field,
                    value=(min_value, max_value),
                    original_value=(min_value, max_value),
                    type_hints=(type(min_value), type(max_value)),
                )
            )

    def _collect_replacements(
        self,
        node: ast.AST,
        path: Tuple[str, ...],
        offsets: Sequence[int],
        updates: Dict[Tuple[str, ...], RangeEntry],
        replacements: List[Tuple[int, int, str]],
    ) -> None:
        if isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                if key_node is None:
                    continue
                key = ast.literal_eval(key_node)
                if not isinstance(key, str):
                    continue
                self._collect_replacements(value_node, path + (key,), offsets, updates, replacements)
            return

        if isinstance(node, ast.Tuple) and len(node.elts) == 2 and path in updates:
            entry = updates[path]
            if node.end_lineno is None or node.end_col_offset is None:
                raise ValueError("无法定位范围值在文件中的结束位置")
            start = _position_to_offset(offsets, node.lineno, node.col_offset)
            end = _position_to_offset(offsets, node.end_lineno, node.end_col_offset)
            replacements.append((start, end, self._format_tuple(entry.value, entry.type_hints)))

    @staticmethod
    def _split_path(path: Tuple[str, ...]) -> Tuple[str, str]:
        if len(path) >= 3:
            return path[1], path[2]
        if len(path) == 2:
            return path[1], "范围"
        if len(path) == 1:
            return path[0], "范围"
        return "unknown", "范围"

    @staticmethod
    def _format_tuple(value: RangeTuple, type_hints: Tuple[type, type]) -> str:
        return f"({RuleFileParser._format_number(value[0], type_hints[0])}, {RuleFileParser._format_number(value[1], type_hints[1])})"

    @staticmethod
    def _format_number(value: float | int, type_hint: type) -> str:
        if type_hint is int and float(value).is_integer():
            return str(int(round(float(value))))

        text = f"{float(value):.6f}".rstrip("0").rstrip(".")
        if "." not in text:
            text += ".0"
        return text


class RuleRangeRepository:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.specs_by_assignment = {spec.assignment_name: spec for spec in RULE_SPECS}
        self.specs_by_file: Dict[str, List[AssignmentSpec]] = {}
        for spec in RULE_SPECS:
            self.specs_by_file.setdefault(spec.file_name, []).append(spec)

    def load_entries(self) -> List[RangeEntry]:
        entries: List[RangeEntry] = []
        for spec in RULE_SPECS:
            parser = RuleFileParser(self.base_dir / spec.file_name)
            entries.extend(parser.parse_entries(spec.assignment_name, spec.label))
        return entries

    def save_entries(self, entries: Iterable[RangeEntry]) -> SaveResult:
        dirty_entries = [entry for entry in entries if entry.is_dirty]
        if not dirty_entries:
            return SaveResult(changed_count=0, backup_dir=None)

        by_file: Dict[str, List[RangeEntry]] = {}
        for entry in dirty_entries:
            by_file.setdefault(entry.file_name, []).append(entry)

        changed_count = 0
        backup_dir = self._create_backup_dir()
        for file_name, file_entries in by_file.items():
            file_path = self.base_dir / file_name
            source_text = file_path.read_text(encoding="utf-8")
            self._backup_file(file_path, backup_dir)
            replacements: List[Tuple[int, int, str]] = []
            parser = RuleFileParser(file_path)
            assignments: Dict[str, Dict[Tuple[str, ...], RangeEntry]] = {}
            for entry in file_entries:
                assignments.setdefault(entry.assignment_name, {})[entry.path] = entry

            for assignment_name, updates in assignments.items():
                replacements.extend(parser.build_replacements(assignment_name, updates))

            if not replacements:
                continue

            replacements.sort(key=lambda item: item[0], reverse=True)
            for start, end, replacement_text in replacements:
                source_text = source_text[:start] + replacement_text + source_text[end:]
                changed_count += 1

            file_path.write_text(source_text, encoding="utf-8")

        for entry in dirty_entries:
            entry.original_value = entry.value

        return SaveResult(changed_count=changed_count, backup_dir=backup_dir)

    def _create_backup_dir(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.base_dir / "backups" / "rule_range_editor" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @staticmethod
    def _backup_file(file_path: Path, backup_dir: Path) -> None:
        backup_path = backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)


class RuleRangeEditorApp:
    def __init__(self, root: tk.Tk, repository: RuleRangeRepository):
        self.root = root
        self.repository = repository
        self.entries = repository.load_entries()
        self.entry_by_id: Dict[str, RangeEntry] = {}
        self.current_scope: Tuple[str, str | None] | None = None
        self.active_editor: tk.Entry | None = None
        self.is_generating = False

        self.root.title("EFT 规则范围编辑器")
        self.root.geometry("1240x760")
        self.root.minsize(980, 620)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.detail_var = tk.StringVar()

        self._build_layout()
        self._populate_scope_tree()
        self._refresh_table()
        self._update_status()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(12, 10))
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        toolbar.columnconfigure(4, weight=1)

        ttk.Button(toolbar, text="保存全部", command=self.save_all).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(toolbar, text="重新加载", command=self.reload_entries).grid(row=0, column=1, padx=(0, 12))
        self.generate_button = ttk.Button(toolbar, text="生成补丁", command=self.generate_patch)
        self.generate_button.grid(row=0, column=2, padx=(0, 12))
        ttk.Label(toolbar, text="搜索:").grid(row=0, column=3, sticky="w")
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        search_entry.grid(row=0, column=4, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_table())

        left_panel = ttk.Frame(self.root, padding=(12, 0, 8, 12))
        left_panel.grid(row=1, column=0, sticky="ns")
        left_panel.rowconfigure(0, weight=1)

        right_panel = ttk.Frame(self.root, padding=(8, 0, 12, 12))
        right_panel.grid(row=1, column=1, sticky="nsew")
        right_panel.rowconfigure(1, weight=1)
        right_panel.rowconfigure(2, weight=0)
        right_panel.columnconfigure(0, weight=1)

        self.scope_tree = ttk.Treeview(left_panel, show="tree", height=28)
        self.scope_tree.grid(row=0, column=0, sticky="ns")
        self.scope_tree.bind("<<TreeviewSelect>>", self._on_scope_selected)

        ttk.Label(right_panel, text="双击最小值/最大值即可编辑，保存时会直接写回原规则文件。", anchor="w").grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        columns = ("profile", "field", "min", "max", "source")
        self.table = ttk.Treeview(right_panel, columns=columns, show="headings")
        self.table.heading("profile", text="档位")
        self.table.heading("field", text="字段")
        self.table.heading("min", text="最小值")
        self.table.heading("max", text="最大值")
        self.table.heading("source", text="来源")
        self.table.column("profile", width=220, anchor="w")
        self.table.column("field", width=180, anchor="w")
        self.table.column("min", width=120, anchor="center")
        self.table.column("max", width=120, anchor="center")
        self.table.column("source", width=180, anchor="w")
        self.table.grid(row=1, column=0, sticky="nsew")
        self.table.bind("<Double-1>", self._begin_edit)
        self.table.bind("<<TreeviewSelect>>", self._on_table_selected)
        self.table.tag_configure("dirty", background="#fff4cc")

        scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        detail_frame = ttk.LabelFrame(right_panel, text="字段说明", padding=(10, 8))
        detail_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        detail_frame.columnconfigure(0, weight=1)

        self.detail_text = tk.Text(
            detail_frame,
            height=7,
            wrap="word",
            relief="flat",
            background=self.root.cget("background"),
        )
        self.detail_text.grid(row=0, column=0, sticky="ew")
        self.detail_text.configure(state="disabled")

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(12, 6))
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

    def _populate_scope_tree(self) -> None:
        self.scope_tree.delete(*self.scope_tree.get_children())
        grouped: Dict[str, Dict[str, str]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.assignment_label, {})[entry.profile] = entry.assignment_name

        for label in [spec.label for spec in RULE_SPECS]:
            if label not in grouped:
                continue
            root_id = self.scope_tree.insert("", "end", text=label, values=(label,))
            profiles = sorted(grouped[label])
            for profile in profiles:
                self.scope_tree.insert(root_id, "end", text=profile, values=(label, profile))
            self.scope_tree.item(root_id, open=True)

        root_nodes = self.scope_tree.get_children()
        if root_nodes:
            first = root_nodes[0]
            self.scope_tree.selection_set(first)
            self._set_scope_from_item(first)

    def _set_scope_from_item(self, item_id: str) -> None:
        parent = self.scope_tree.parent(item_id)
        if not parent:
            label = self.scope_tree.item(item_id, "text")
            self.current_scope = (label, None)
            return

        label = self.scope_tree.item(parent, "text")
        profile = self.scope_tree.item(item_id, "text")
        self.current_scope = (label, profile)

    def _on_scope_selected(self, _event: object) -> None:
        selected = self.scope_tree.selection()
        if not selected:
            return
        self._set_scope_from_item(selected[0])
        self._refresh_table()

    def _refresh_table(self) -> None:
        if self.active_editor is not None:
            self.active_editor.destroy()
            self.active_editor = None

        self.table.delete(*self.table.get_children())
        self.entry_by_id.clear()

        search_text = self.search_var.get().strip().lower()
        visible_entries = sorted(self._filtered_entries(search_text), key=lambda entry: (entry.assignment_label, entry.profile, entry.field))

        for entry in visible_entries:
            item_id = self.table.insert(
                "",
                "end",
                values=(
                    entry.profile,
                    entry.field,
                    self._display_number(entry.value[0]),
                    self._display_number(entry.value[1]),
                    entry.assignment_label,
                ),
                tags=("dirty",) if entry.is_dirty else (),
            )
            self.entry_by_id[item_id] = entry

        items = self.table.get_children()
        if items:
            first_item = items[0]
            self.table.selection_set(first_item)
            self._update_field_details(self.entry_by_id[first_item])
        else:
            self._update_field_details(None)

        self._update_status()

    def _filtered_entries(self, search_text: str) -> List[RangeEntry]:
        result: List[RangeEntry] = []
        for entry in self.entries:
            if self.current_scope is not None:
                scope_label, scope_profile = self.current_scope
                if entry.assignment_label != scope_label:
                    continue
                if scope_profile and entry.profile != scope_profile:
                    continue

            if search_text:
                haystack = " ".join((entry.assignment_label, entry.profile, entry.field, entry.file_name)).lower()
                if search_text not in haystack:
                    continue

            result.append(entry)
        return result

    def _begin_edit(self, event: tk.Event) -> None:
        region = self.table.identify("region", event.x, event.y)
        if region != "cell":
            return

        item_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        if not item_id or column_id not in {"#3", "#4"}:
            return

        if self.active_editor is not None:
            self.active_editor.destroy()
            self.active_editor = None

        x, y, width, height = self.table.bbox(item_id, column_id)
        current_text = self.table.set(item_id, column_id)
        entry = ttk.Entry(self.table)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_text)
        entry.select_range(0, tk.END)
        entry.focus_set()
        entry.bind("<Return>", lambda _event: self._commit_edit(item_id, column_id, entry.get()))
        entry.bind("<Escape>", lambda _event: self._cancel_edit())
        entry.bind("<FocusOut>", lambda _event: self._commit_edit(item_id, column_id, entry.get()))
        self.active_editor = entry

    def _on_table_selected(self, _event: object) -> None:
        selected = self.table.selection()
        if not selected:
            self._update_field_details(None)
            return
        self._update_field_details(self.entry_by_id.get(selected[0]))

    def _commit_edit(self, item_id: str, column_id: str, raw_value: str) -> None:
        if self.active_editor is None:
            return

        entry = self.entry_by_id[item_id]
        try:
            parsed_value = self._parse_number(raw_value)
        except ValueError:
            messagebox.showerror("输入无效", "请输入整数或小数。")
            self.active_editor.focus_set()
            return

        min_value, max_value = entry.value
        if column_id == "#3":
            min_value = parsed_value
        else:
            max_value = parsed_value

        if min_value > max_value:
            messagebox.showerror("范围无效", "最小值不能大于最大值。")
            self.active_editor.focus_set()
            return

        entry.value = (min_value, max_value)
        self.active_editor.destroy()
        self.active_editor = None
        self._refresh_table()

    def _cancel_edit(self) -> None:
        if self.active_editor is not None:
            self.active_editor.destroy()
            self.active_editor = None

    def save_all(self) -> None:
        try:
            save_result = self.repository.save_entries(self.entries)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            return

        if save_result.changed_count == 0:
            messagebox.showinfo("无需保存", "当前没有待写入的修改。")
            return

        self._refresh_table()
        backup_text = str(save_result.backup_dir) if save_result.backup_dir else "未创建备份"
        messagebox.showinfo("保存完成", f"已写回 {save_result.changed_count} 处范围值。\n备份目录: {backup_text}")

    def reload_entries(self) -> None:
        if any(entry.is_dirty for entry in self.entries):
            confirmed = messagebox.askyesno("放弃修改", "当前有未保存修改，确认重新加载吗？")
            if not confirmed:
                return

        try:
            self.entries = self.repository.load_entries()
        except Exception as exc:
            messagebox.showerror("重新加载失败", str(exc))
            return

        self._populate_scope_tree()
        self._refresh_table()

    def on_close(self) -> None:
        if self.is_generating:
            messagebox.showwarning("仍在生成", "当前正在生成补丁，请等待完成后再关闭窗口。")
            return
        if any(entry.is_dirty for entry in self.entries):
            confirmed = messagebox.askyesno("未保存修改", "还有未保存修改，确认直接退出吗？")
            if not confirmed:
                return
        self.root.destroy()

    def _update_status(self) -> None:
        total = len(self.entries)
        dirty = sum(1 for entry in self.entries if entry.is_dirty)
        visible = len(self.table.get_children())
        self.status_var.set(f"总范围项: {total}    当前显示: {visible}    未保存修改: {dirty}")

    def _update_field_details(self, entry: RangeEntry | None) -> None:
        if entry is None:
            self._set_detail_text("选择一条规则后，这里会显示字段作用、方向提示和当前规则类别说明。")
            return

        field_explanation = FIELD_EXPLANATIONS.get(entry.field, "该字段暂无专门说明，通常需要结合所属规则档位和数值方向一起判断。")
        assignment_explanation = ASSIGNMENT_EXPLANATIONS.get(entry.assignment_name, "该规则分类暂无额外说明。")
        trend_hint = TREND_HINTS.get(entry.field, "该字段没有预设方向提示，请结合游戏手感和该规则类别语义判断。")

        detail_lines = [
            f"字段: {entry.field}",
            f"档位: {entry.profile}",
            f"分类: {entry.assignment_label}",
            f"当前范围: {self._display_number(entry.value[0])} ~ {self._display_number(entry.value[1])}",
            "",
            f"字段作用: {field_explanation}",
            f"方向提示: {trend_hint}",
            f"规则说明: {assignment_explanation}",
        ]
        self._set_detail_text("\n".join(detail_lines))

    def _set_detail_text(self, text: str) -> None:
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def generate_patch(self) -> None:
        if self.is_generating:
            return

        if any(entry.is_dirty for entry in self.entries):
            confirmed = messagebox.askyesno("未保存修改", "检测到未保存的规则修改。是否先保存再生成补丁？")
            if confirmed:
                self.save_all()
                if any(entry.is_dirty for entry in self.entries):
                    return

        self.is_generating = True
        self.generate_button.configure(state="disabled")
        self.status_var.set("正在生成补丁，请稍候...")

        worker = threading.Thread(target=self._run_generate_patch, daemon=True)
        worker.start()

    def _run_generate_patch(self) -> None:
        command = [sys.executable, "generate_realism_patch.py"]
        try:
            completed = subprocess.run(
                command,
                cwd=self.repository.base_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.root.after(0, lambda: self._on_generate_complete(completed.returncode, completed.stdout, completed.stderr))
        except Exception as exc:
            self.root.after(0, lambda: self._on_generate_failed(str(exc)))

    def _on_generate_complete(self, return_code: int, stdout: str, stderr: str) -> None:
        self.is_generating = False
        self.generate_button.configure(state="normal")

        if return_code == 0:
            summary = self._summarize_output(stdout)
            self.status_var.set("补丁生成完成")
            messagebox.showinfo("生成完成", f"补丁已生成到 output 目录。\n\n摘要:\n{summary}")
            return

        summary = self._summarize_output(stderr or stdout)
        self.status_var.set("补丁生成失败")
        messagebox.showerror("生成失败", f"生成器退出码: {return_code}\n\n摘要:\n{summary}")

    def _on_generate_failed(self, error_text: str) -> None:
        self.is_generating = False
        self.generate_button.configure(state="normal")
        self.status_var.set("补丁生成失败")
        messagebox.showerror("生成失败", error_text)

    @staticmethod
    def _summarize_output(output: str, max_lines: int = 12) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return "无输出。"
        selected = lines[-max_lines:]
        return "\n".join(selected)

    @staticmethod
    def _parse_number(raw_value: str) -> float | int:
        text = raw_value.strip()
        if not text:
            raise ValueError("empty")
        if any(char in text for char in (".", "e", "E")):
            return float(text)
        return int(text)

    @staticmethod
    def _display_number(value: float | int) -> str:
        if isinstance(value, int):
            return str(value)
        text = f"{float(value):.6f}".rstrip("0").rstrip(".")
        if "." not in text:
            text += ".0"
        return text


def run_check(base_dir: Path) -> int:
    repository = RuleRangeRepository(base_dir)
    entries = repository.load_entries()
    print(f"loaded rule range entries: {len(entries)}")
    for spec in RULE_SPECS:
        count = sum(1 for entry in entries if entry.assignment_name == spec.assignment_name and entry.file_name == spec.file_name)
        print(f"- {spec.label}: {count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="编辑规则范围的GUI工具")
    parser.add_argument("--check", action="store_true", help="仅检查规则文件是否可解析，不启动GUI")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    if args.check:
        return run_check(base_dir)

    root = tk.Tk()
    app = RuleRangeEditorApp(root, RuleRangeRepository(base_dir))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())