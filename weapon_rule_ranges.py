# -*- coding: utf-8 -*-
"""武器规则范围配置。

将武器规则范围独立到此文件，便于用户直接调整数值区间。
"""

# 武器规则范围（来自“武器属性规则指南”）
WEAPON_PROFILE_RANGES = {
    "assault": {
        "VerticalRecoil": (80, 95),
        "HorizontalRecoil": (160, 200),
        "Convergence": (2, 25),
        "Dispersion": (4, 8),
        "VisualMulti": (1.1, 1.3),
        "Ergonomics": (80, 90),
        "RecoilIntensity": (0.15, 0.25),
    },
    "pistol": {
        "VerticalRecoil": (450, 650),
        "HorizontalRecoil": (400, 600),
        "Convergence": (14, 18),
        "Dispersion": (10, 18),
        "VisualMulti": (2.3, 2.8),
        "BaseTorque": (-2.0, -1.0),
    },
    "smg": {
        "VerticalRecoil": (30, 55),
        "HorizontalRecoil": (80, 140),
        "Convergence": (16, 22),
        "Dispersion": (6, 12),
        "VisualMulti": (0.9, 1.2),
        "RecoilIntensity": (0.1, 0.18),
    },
    "sniper": {
        "VerticalRecoil": (130, 250),
        "HorizontalRecoil": (180, 350),
        "Convergence": (8, 13),
        "Dispersion": (0.5, 3.0),
        "VisualMulti": (1.2, 2.0),
    },
    "shotgun": {
        "VerticalRecoil": (300, 500),
        "HorizontalRecoil": (300, 550),
        "Dispersion": (15, 30),
        "VisualMulti": (2.0, 2.5),
        "RecoilIntensity": (0.4, 0.6),
        "ShotgunDispersion": (1, 1),
    },
}
