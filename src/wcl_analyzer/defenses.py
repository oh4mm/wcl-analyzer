"""常见减伤 / 药水 / 主动治疗饰品目录。

按 spell ID 匹配（优先），名称仅作兜底。可在 DEFENSE_ABILITIES 末尾继续追加。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DefenseCategory(str, Enum):
    PERSONAL = "personal"
    RAID = "raid"
    HEAL_POTION = "heal_potion"
    COMBAT_POTION = "combat_potion"
    HEAL_TRINKET = "heal_trinket"
    INTERRUPT = "interrupt"


CATEGORY_LABELS = {
    DefenseCategory.PERSONAL: "个减",
    DefenseCategory.RAID: "团减",
    DefenseCategory.HEAL_POTION: "治疗药水",
    DefenseCategory.COMBAT_POTION: "爆发药水",
    DefenseCategory.HEAL_TRINKET: "治疗饰品",
    DefenseCategory.INTERRUPT: "打断",
}

CATEGORY_ALIASES = {
    "个减": DefenseCategory.PERSONAL,
    "个人减伤": DefenseCategory.PERSONAL,
    "personal": DefenseCategory.PERSONAL,
    "团减": DefenseCategory.RAID,
    "团队减伤": DefenseCategory.RAID,
    "raid": DefenseCategory.RAID,
    "治疗药水": DefenseCategory.HEAL_POTION,
    "heal_potion": DefenseCategory.HEAL_POTION,
    "heal": DefenseCategory.HEAL_POTION,
    "爆发药水": DefenseCategory.COMBAT_POTION,
    "combat_potion": DefenseCategory.COMBAT_POTION,
    "combat": DefenseCategory.COMBAT_POTION,
    "治疗饰品": DefenseCategory.HEAL_TRINKET,
    "heal_trinket": DefenseCategory.HEAL_TRINKET,
    "trinket": DefenseCategory.HEAL_TRINKET,
    "打断": DefenseCategory.INTERRUPT,
    "interrupt": DefenseCategory.INTERRUPT,
    "interrupts": DefenseCategory.INTERRUPT,
}


@dataclass(frozen=True)
class DefenseAbility:
    spell_id: int
    name: str
    category: DefenseCategory
    aliases: tuple[str, ...] = ()


# 只收录真实个减 / 墙 / 团减、药水、主动治疗饰品，以及打断。
# 不收坦克吞吐自疗或纯治疗类技能（如灵界打击、狂暴回复、意气风发等）。
# 药水 / 饰品以战斗日志中的 spell ID（item use）为准，不是物品 ID。
DEFENSE_ABILITIES: tuple[DefenseAbility, ...] = (
    # —— 个减：死亡骑士 ——
    DefenseAbility(48707, "反魔法护罩", DefenseCategory.PERSONAL, ("Anti-Magic Shell",)),
    DefenseAbility(48792, "冰封之韧", DefenseCategory.PERSONAL, ("Icebound Fortitude",)),
    DefenseAbility(55233, "吸血鬼之血", DefenseCategory.PERSONAL, ("Vampiric Blood",)),
    DefenseAbility(49039, "巫妖之躯", DefenseCategory.PERSONAL, ("Lichborne",)),
    # —— 个减：恶魔猎手 ——
    DefenseAbility(198589, "疾影", DefenseCategory.PERSONAL, ("Blur",)),
    DefenseAbility(196555, "虚空行走", DefenseCategory.PERSONAL, ("Netherwalk",)),
    DefenseAbility(203720, "恶魔尖刺", DefenseCategory.PERSONAL, ("Demon Spikes",)),
    DefenseAbility(204021, "烈火烙印", DefenseCategory.PERSONAL, ("Fiery Brand",)),
    DefenseAbility(187827, "恶魔变形", DefenseCategory.PERSONAL, ("Metamorphosis",)),
    # —— 个减：德鲁伊 ——
    DefenseAbility(22812, "树皮术", DefenseCategory.PERSONAL, ("Barkskin",)),
    DefenseAbility(102342, "铁木树皮", DefenseCategory.PERSONAL, ("Ironbark",)),
    DefenseAbility(61336, "生存本能", DefenseCategory.PERSONAL, ("Survival Instincts",)),
    # —— 个减：唤魔师 ——
    DefenseAbility(363916, "黑曜鳞片", DefenseCategory.PERSONAL, ("Obsidian Scales",)),
    DefenseAbility(374348, "新生烈焰", DefenseCategory.PERSONAL, ("Renewing Blaze",)),
    DefenseAbility(370960, "翡翠交融", DefenseCategory.PERSONAL, ("Emerald Communion",)),
    # —— 个减：猎人 ——
    DefenseAbility(186265, "灵龟守护", DefenseCategory.PERSONAL, ("Aspect of the Turtle",)),
    DefenseAbility(264735, "适者生存", DefenseCategory.PERSONAL, ("Survival of the Fittest",)),
    DefenseAbility(53480, "牺牲咆哮", DefenseCategory.PERSONAL, ("Roar of Sacrifice",)),
    # —— 个减：法师 ——
    DefenseAbility(45438, "寒冰屏障", DefenseCategory.PERSONAL, ("Ice Block",)),
    DefenseAbility(414658, "深寒", DefenseCategory.PERSONAL, ("Ice Cold",)),
    DefenseAbility(55342, "镜像", DefenseCategory.PERSONAL, ("Mirror Image",)),
    DefenseAbility(110959, "强化隐形术", DefenseCategory.PERSONAL, ("Greater Invisibility",)),
    DefenseAbility(342245, "改变时间", DefenseCategory.PERSONAL, ("Alter Time",)),
    DefenseAbility(235450, "棱光屏障", DefenseCategory.PERSONAL, ("Prismatic Barrier",)),
    DefenseAbility(235313, "烈焰护体", DefenseCategory.PERSONAL, ("Blazing Barrier",)),
    DefenseAbility(11426, "寒冰护体", DefenseCategory.PERSONAL, ("Ice Barrier",)),
    # —— 个减：武僧 ——
    DefenseAbility(115203, "壮胆酒", DefenseCategory.PERSONAL, ("Fortifying Brew",)),
    DefenseAbility(122783, "散魔功", DefenseCategory.PERSONAL, ("Diffuse Magic",)),
    DefenseAbility(122278, "躯不坏", DefenseCategory.PERSONAL, ("Dampen Harm",)),
    DefenseAbility(122470, "业报之触", DefenseCategory.PERSONAL, ("Touch of Karma",)),
    DefenseAbility(116849, "作茧缚命", DefenseCategory.PERSONAL, ("Life Cocoon",)),
    DefenseAbility(115176, "禅悟冥想", DefenseCategory.PERSONAL, ("Zen Meditation",)),
    # —— 个减：圣骑士 ——
    DefenseAbility(642, "圣盾术", DefenseCategory.PERSONAL, ("Divine Shield",)),
    DefenseAbility(498, "圣佑术", DefenseCategory.PERSONAL, ("Divine Protection",)),
    DefenseAbility(403876, "圣佑术", DefenseCategory.PERSONAL, ("Divine Protection",)),
    DefenseAbility(1022, "保护祝福", DefenseCategory.PERSONAL, ("Blessing of Protection",)),
    DefenseAbility(204018, "破咒祝福", DefenseCategory.PERSONAL, ("Blessing of Spellwarding",)),
    DefenseAbility(6940, "牺牲祝福", DefenseCategory.PERSONAL, ("Blessing of Sacrifice",)),
    DefenseAbility(31850, "炽热防御者", DefenseCategory.PERSONAL, ("Ardent Defender",)),
    DefenseAbility(86659, "远古列王守卫", DefenseCategory.PERSONAL, ("Guardian of Ancient Kings",)),
    DefenseAbility(633, "圣疗术", DefenseCategory.PERSONAL, ("Lay on Hands",)),
    DefenseAbility(31884, "复仇之怒", DefenseCategory.PERSONAL, ("Avenging Wrath",)),
    # —— 个减：牧师 ——
    DefenseAbility(47585, "消散", DefenseCategory.PERSONAL, ("Dispersion",)),
    DefenseAbility(19236, "绝望祷言", DefenseCategory.PERSONAL, ("Desperate Prayer",)),
    DefenseAbility(586, "渐隐术", DefenseCategory.PERSONAL, ("Fade",)),
    DefenseAbility(33206, "痛苦压制", DefenseCategory.PERSONAL, ("Pain Suppression",)),
    DefenseAbility(47788, "守护之魂", DefenseCategory.PERSONAL, ("Guardian Spirit",)),
    # —— 个减：潜行者 ——
    DefenseAbility(31224, "暗影斗篷", DefenseCategory.PERSONAL, ("Cloak of Shadows",)),
    DefenseAbility(5277, "闪避", DefenseCategory.PERSONAL, ("Evasion",)),
    DefenseAbility(1966, "佯攻", DefenseCategory.PERSONAL, ("Feint",)),
    # —— 个减：萨满 ——
    DefenseAbility(108271, "星界转移", DefenseCategory.PERSONAL, ("Astral Shift",)),
    DefenseAbility(198838, "大地之墙图腾", DefenseCategory.PERSONAL, ("Earthen Wall Totem",)),
    DefenseAbility(198103, "土元素", DefenseCategory.PERSONAL, ("Earth Elemental",)),
    # —— 个减：术士 ——
    DefenseAbility(104773, "不灭决心", DefenseCategory.PERSONAL, ("Unending Resolve",)),
    DefenseAbility(108416, "黑暗契约", DefenseCategory.PERSONAL, ("Dark Pact",)),
    # —— 个减：战士 ——
    DefenseAbility(871, "盾墙", DefenseCategory.PERSONAL, ("Shield Wall",)),
    DefenseAbility(12975, "破釜沉舟", DefenseCategory.PERSONAL, ("Last Stand",)),
    DefenseAbility(118038, "剑在人在", DefenseCategory.PERSONAL, ("Die by the Sword",)),
    DefenseAbility(23920, "法术反射", DefenseCategory.PERSONAL, ("Spell Reflection",)),
    DefenseAbility(184364, "狂怒回复", DefenseCategory.PERSONAL, ("Enraged Regeneration",)),
    DefenseAbility(190456, "无视苦痛", DefenseCategory.PERSONAL, ("Ignore Pain",)),
    DefenseAbility(386208, "防御姿态", DefenseCategory.PERSONAL, ("Defensive Stance",)),
    # —— 团减 ——
    DefenseAbility(51052, "反魔法领域", DefenseCategory.RAID, ("Anti-Magic Zone",)),
    DefenseAbility(62618, "真言术：障", DefenseCategory.RAID, ("Power Word: Barrier",)),
    DefenseAbility(271466, "微光屏障", DefenseCategory.RAID, ("Luminous Barrier",)),
    DefenseAbility(31821, "光环掌握", DefenseCategory.RAID, ("Aura Mastery",)),
    DefenseAbility(97462, "集结呐喊", DefenseCategory.RAID, ("Rallying Cry",)),
    DefenseAbility(196718, "黑暗", DefenseCategory.RAID, ("Darkness",)),
    DefenseAbility(98008, "灵魂链接图腾", DefenseCategory.RAID, ("Spirit Link Totem",)),
    DefenseAbility(374227, "微风", DefenseCategory.RAID, ("Zephyr",)),
    DefenseAbility(414660, "群体屏障", DefenseCategory.RAID, ("Mass Barrier",)),
    DefenseAbility(363534, "扭转乾坤", DefenseCategory.RAID, ("Rewind",)),
    DefenseAbility(740, "宁静", DefenseCategory.RAID, ("Tranquility",)),
    DefenseAbility(115310, "还魂术", DefenseCategory.RAID, ("Revival",)),
    DefenseAbility(64843, "神圣赞美诗", DefenseCategory.RAID, ("Divine Hymn",)),
    DefenseAbility(265202, "圣言术：赎", DefenseCategory.RAID, ("Holy Word: Salvation",)),
    DefenseAbility(15286, "吸血鬼的拥抱", DefenseCategory.RAID, ("Vampiric Embrace",)),
    # —— 治疗药水 / 治疗石 ——
    DefenseAbility(6262, "治疗石", DefenseCategory.HEAL_POTION, ("Healthstone", "造血石")),
    DefenseAbility(431416, "阿加治疗药水", DefenseCategory.HEAL_POTION, ("Algari Healing Potion",)),
    # item-use 变体（与 431416 同名，WCL Casts 常见）
    DefenseAbility(431418, "阿加治疗药水", DefenseCategory.HEAL_POTION, ("Algari Healing Potion",)),
    DefenseAbility(431419, "穴居者的愉悦", DefenseCategory.HEAL_POTION, ("Cavedweller's Delight",)),
    DefenseAbility(460074, "怪诞之瓶", DefenseCategory.HEAL_POTION, ("Grotesque Vial",)),
    DefenseAbility(1238009, "活力治疗药水", DefenseCategory.HEAL_POTION, ("Invigorating Healing Potion",)),
    DefenseAbility(207023, "梦行者治疗药水", DefenseCategory.HEAL_POTION, ("Dreamwalker's Healing Potion",)),
    DefenseAbility(370511, "凋零活力药水", DefenseCategory.HEAL_POTION, ("Potion of Withering Vitality",)),
    DefenseAbility(371149, "凋零梦境药水", DefenseCategory.HEAL_POTION, ("Potion of Withering Dreams",)),
    DefenseAbility(250871, "海滨治疗药水", DefenseCategory.HEAL_POTION, ("Coastal Healing Potion",)),
    DefenseAbility(1262857, "强效治疗药水", DefenseCategory.HEAL_POTION, ("Potent Healing Potion",)),
    # Midnight
    DefenseAbility(
        1295247,
        "浓缩银月城生命药水",
        DefenseCategory.HEAL_POTION,
        ("Concentrated Silvermoon Health Potion",),
    ),
    # —— 爆发药水（战斗药水） ——
    DefenseAbility(431932, "回火药水", DefenseCategory.COMBAT_POTION, ("Tempered Potion",)),
    DefenseAbility(431914, "坚定专注药水", DefenseCategory.COMBAT_POTION, ("Potion of Unwavering Focus",)),
    DefenseAbility(431925, "前线药水", DefenseCategory.COMBAT_POTION, ("Frontline Potion",)),
    DefenseAbility(431941, "重生猎豹药水", DefenseCategory.COMBAT_POTION, ("Potion of the Reborn Cheetah",)),
    DefenseAbility(371024, "元素究极强能药水", DefenseCategory.COMBAT_POTION, ("Elemental Potion of Ultimate Power",)),
    DefenseAbility(371028, "元素强能药水", DefenseCategory.COMBAT_POTION, ("Elemental Potion of Power",)),
    DefenseAbility(307162, "幻影火焰药水", DefenseCategory.COMBAT_POTION, ("Potion of Spectral Intellect",)),
    DefenseAbility(307159, "幻影敏捷药水", DefenseCategory.COMBAT_POTION, ("Potion of Spectral Agility",)),
    DefenseAbility(307164, "幻影力量药水", DefenseCategory.COMBAT_POTION, ("Potion of Spectral Strength",)),
    # Midnight
    DefenseAbility(
        1236994,
        "鲁莽药水",
        DefenseCategory.COMBAT_POTION,
        ("Potion of Recklessness",),
    ),
    DefenseAbility(
        1295132,
        "液态光泽",
        DefenseCategory.COMBAT_POTION,
        ("Liquid Luster",),
    ),
    DefenseAbility(
        1236616,
        "圣光潜力",
        DefenseCategory.COMBAT_POTION,
        ("Light's Potential",),
    ),
    # —— 治疗饰品（主动 on-use；以 WCL Casts 中出现的 spell ID 为准） ——
    DefenseAbility(
        1232721,
        "卢米萨尔的活体丝绸",
        DefenseCategory.HEAL_TRINKET,
        ("Loom'ithar's Living Silk",),
    ),
    DefenseAbility(
        450561,
        "梅雷达尔的钟声",
        DefenseCategory.HEAL_TRINKET,
        ("Mereldar's Toll",),
    ),
    DefenseAbility(
        443539,
        "梅雷达尔的钟声",
        DefenseCategory.HEAL_TRINKET,
        ("Mereldar's Toll",),
    ),
    DefenseAbility(
        443536,
        "迸发光片",
        DefenseCategory.HEAL_TRINKET,
        ("Bursting Lightshard",),
    ),
    DefenseAbility(
        1220488,
        "暗索医疗直升机",
        DefenseCategory.HEAL_TRINKET,
        ("Darkfuse Medichopper",),
    ),
    DefenseAbility(
        471214,
        "加乐宫侍酒服务",
        DefenseCategory.HEAL_TRINKET,
        ("Gallagio Bottle Service",),
    ),
    DefenseAbility(
        444282,
        "蠕行凝块",
        DefenseCategory.HEAL_TRINKET,
        ("Creeping Coagulum",),
    ),
    DefenseAbility(
        443531,
        "隐修院玺戒",
        DefenseCategory.HEAL_TRINKET,
        ("Bolstering Light", "Signet of the Priory"),
    ),
    DefenseAbility(
        368509,
        "索·莉亚的隐秘技",
        DefenseCategory.HEAL_TRINKET,
        ("So'leah's Secret Technique",),
    ),
    DefenseAbility(
        368510,
        "索·莉亚的隐秘技",
        DefenseCategory.HEAL_TRINKET,
        ("So'leah's Secret Technique",),
    ),
    DefenseAbility(
        444959,
        "间谍大师的网",
        DefenseCategory.HEAL_TRINKET,
        ("Spymaster's Web",),
    ),
    # Midnight：on-use 治疗饰品（Casts 里的 spell ID）
    DefenseAbility(
        1291894,
        "盘魂者仪式容器",
        DefenseCategory.HEAL_TRINKET,
        ("Soulcoiler Ritual Vessel",),
    ),
    DefenseAbility(
        1219198,
        "上餐了！",
        DefenseCategory.HEAL_TRINKET,
        ("Order Up!", "Emerald Coach's Whistle"),
    ),
    # —— 打断（页面默认隐藏，勾选「显示打断」后出现在玩家泳道）——
    DefenseAbility(1766, "脚踢", DefenseCategory.INTERRUPT, ("Kick",)),
    DefenseAbility(6552, "拳击", DefenseCategory.INTERRUPT, ("Pummel",)),
    DefenseAbility(2139, "法术反制", DefenseCategory.INTERRUPT, ("Counterspell",)),
    DefenseAbility(57994, "风剪", DefenseCategory.INTERRUPT, ("Wind Shear",)),
    DefenseAbility(106839, "迎头痛击", DefenseCategory.INTERRUPT, ("Skull Bash",)),
    DefenseAbility(93985, "迎头痛击", DefenseCategory.INTERRUPT, ("Skull Bash",)),
    DefenseAbility(97547, "日光术", DefenseCategory.INTERRUPT, ("Solar Beam",)),
    DefenseAbility(47528, "心灵冰冻", DefenseCategory.INTERRUPT, ("Mind Freeze",)),
    DefenseAbility(183752, "瓦解", DefenseCategory.INTERRUPT, ("Disrupt",)),
    DefenseAbility(96231, "责难", DefenseCategory.INTERRUPT, ("Rebuke",)),
    DefenseAbility(116705, "切喉手", DefenseCategory.INTERRUPT, ("Spear Hand Strike",)),
    DefenseAbility(147362, "反制射击", DefenseCategory.INTERRUPT, ("Counter Shot",)),
    DefenseAbility(187707, "压制", DefenseCategory.INTERRUPT, ("Muzzle",)),
    DefenseAbility(351338, "镇压", DefenseCategory.INTERRUPT, ("Quell",)),
    DefenseAbility(15487, "沉默", DefenseCategory.INTERRUPT, ("Silence",)),
    DefenseAbility(119910, "法术封锁", DefenseCategory.INTERRUPT, ("Spell Lock",)),
    DefenseAbility(19647, "法术封锁", DefenseCategory.INTERRUPT, ("Spell Lock",)),
    DefenseAbility(132409, "法术封锁", DefenseCategory.INTERRUPT, ("Spell Lock",)),
    DefenseAbility(78675, "日光术", DefenseCategory.INTERRUPT, ("Solar Beam",)),
)

# 近战 / 自动射击等，不当作首领技能波次标记
# 145629：反魔法领域光环生效（玩家 AMZ 的 Environment「施法」），不是敌方技能
IGNORED_BOSS_ABILITY_IDS = frozenset({1, 75, 6603, 145629})
IGNORED_BOSS_ABILITY_NAMES = frozenset(
    {
        "melee",
        "auto shot",
        "shoot",
        "自动攻击",
        "近战攻击",
        "射击",
        "自动射击",
    }
)

_BY_ID: dict[int, DefenseAbility] = {}
_BY_NAME: dict[str, DefenseAbility] = {}
for _ability in DEFENSE_ABILITIES:
    _BY_ID.setdefault(_ability.spell_id, _ability)
    for _key in (_ability.name, *_ability.aliases):
        _BY_NAME.setdefault(_key.casefold(), _ability)


def category_label(category: DefenseCategory | str) -> str:
    if isinstance(category, DefenseCategory):
        return CATEGORY_LABELS[category]
    try:
        return CATEGORY_LABELS[DefenseCategory(category)]
    except ValueError:
        return str(category)


def parse_category(token: str) -> DefenseCategory:
    key = token.strip().casefold()
    # 中文别名保持原样查找
    mapped = CATEGORY_ALIASES.get(token.strip()) or CATEGORY_ALIASES.get(key)
    if mapped is None:
        raise ValueError(
            f"无法识别的类别：{token}。"
            "可用：个减、团减、治疗药水、爆发药水、治疗饰品、打断。"
        )
    return mapped


def lookup_defense(
    spell_id: int | None = None,
    name: str | None = None,
) -> DefenseAbility | None:
    if spell_id is not None and spell_id in _BY_ID:
        return _BY_ID[spell_id]
    if name:
        return _BY_NAME.get(name.casefold())
    return None


def defense_spell_ids() -> tuple[int, ...]:
    return tuple(_BY_ID.keys())


def is_ignored_boss_ability(spell_id: int | None, name: str | None) -> bool:
    if spell_id is not None and spell_id in IGNORED_BOSS_ABILITY_IDS:
        return True
    if name and name.casefold() in IGNORED_BOSS_ABILITY_NAMES:
        return True
    return False


def build_ability_id_filter(spell_ids: tuple[int, ...] | None = None) -> str:
    ids = spell_ids if spell_ids is not None else defense_spell_ids()
    joined = ", ".join(str(spell_id) for spell_id in ids)
    return f"ability.id in ({joined})"
