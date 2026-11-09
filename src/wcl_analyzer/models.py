from __future__ import annotations

from dataclasses import dataclass


PLAYER_CLASSES = {
    "DeathKnight",
    "DemonHunter",
    "Druid",
    "Evoker",
    "Hunter",
    "Mage",
    "Monk",
    "Paladin",
    "Priest",
    "Rogue",
    "Shaman",
    "Warlock",
    "Warrior",
}

DIFFICULTY_NAMES = {
    1: "随机团队",
    2: "弹性",
    3: "普通",
    4: "英雄",
    5: "史诗",
    8: "挑战",
    10: "史诗钥石",
}

# WCL API 常返回英文 encounter / fight 名；CN 站显示中文。仅作展示别名。
FIGHT_NAME_ZH = {
    # —— 地心之战第 2 赛季大秘境（副本 / 首领 / 小怪）——
    'Cinderbrew Meadery': '燧酿酒庄',
    'Darkflame Cleft': '暗焰裂口',
    'The Rookery': '驭雷栖巢',
    'Priory of the Sacred Flame': '圣焰隐修院',
    'Operation: Floodgate': '水闸行动',
    'The MOTHERLODE!!': '暴富矿区！！',
    'The Motherlode!!': '暴富矿区！！',
    'The Motherlode': '暴富矿区！！',
    'Theater of Pain': '伤逝剧场',
    'Operation: Mechagon': '麦卡贡行动',
    'Operation: Mechagon - Workshop': '麦卡贡行动 - 车间',
    'Operation: Mechagon – Workshop': '麦卡贡行动 - 车间',
    'Mechagon Workshop': '麦卡贡行动 - 车间',
    # 第 2 赛季 NPC（首领 + 小怪，来自 MDT + Wowhead 中文）
    'Adderis': '阿德里斯',
    'Adderis and Aspix': '阿德里斯和阿斯匹克斯',
    'Addled Thug': '混乱的暴徒',
    'Advent Nevermore': '阿德文特·追惘',
    'Aerial Unit R-21/X': 'R-21/X型空中单位',
    'Afflicted Civilian': '痛苦的平民',
    'An Affront of Challengers': '挑战者的怒火',
    'Ancient Captain': '上古队长',
    'Ara-Kara, City of Echoes': '艾拉-卡拉，回响之城',
    'Arathi Footman': '阿拉希步兵',
    'Arathi Knight': '阿拉希骑士',
    'Arathi Neophyte': '阿拉希新兵',
    'Ardent Paladin': '热切的圣骑士',
    'Aspix': '阿斯匹克斯',
    'Avatar of Sethraliss': '塞塔里斯的化身',
    'Azerite Extractor': '艾泽里特提取器',
    'Azerite Footbomb': '艾泽里特足球炸弹',
    'Azerokk': '艾泽洛克',
    'B.O.O.M.B.A.': '王牌轰炸机',
    'Baron Braunpyke': '布朗派克男爵',
    'Battlefield Ritualist': '战场祭师',
    'Bee Wrangler': '驯蜂者',
    'Bee-let': '小蜜蜂',
    'Benk Buzzbee': '本克·鸣蜂',
    'Big M.O.M.M.A.': '老大娘',
    'Big Money Crab': '值钱的螃蟹',
    'Blastatron X-80': '爆破金刚X-80型',
    'Blazikon': '布雷炙孔',
    'Blazing Fiend': '炽焰魔',
    'Blighted Sludge-Spewer': '凋零淤泥喷射者',
    'Bomb Tonk': '炸弹坦克',
    'Bombshell Crab': '爆壳螃蟹',
    'Bone Magus': '白骨魔导师',
    'Brew Drop': '酒滴',
    'Brew Master Aldryr': '酿造大师阿德里尔',
    'Brewmaster Aldryr': '酿造大师阿德里尔',
    'Bront': '布隆特',
    'Captain Dailcry': '戴尔克莱上尉',
    'Careless Hopgoblin': '粗心的酒花大地精',
    'Chef Chewie': '主厨丘伊',
    'City of Threads': '千丝之城',
    'Coalescing Void Diffuser': '凝虚散播者',
    'Coin-Operated Crowd Pummeler': '投币式群体打击者',
    'Consuming Voidstone': '吞噬虚空石',
    'Corridor Creeper': '通道爬行者',
    'Corridor Sleeper': '通道沉眠者',
    'Corrupted Oracle': '被腐化的先知',
    'Crawler Mine': '蛛形地雷',
    'Cursed Rookguard': '被诅咒的雷鸫守卫',
    'Cursed Rooktender': '被诅咒的雷鸫看护者',
    'Cursed Thunderer': '被诅咒的雷霆使',
    'Darkfuse Bloodwarper': '暗索扭血者',
    'Darkfuse Demolitionist': '暗索爆破手',
    'Darkfuse Hyena': '暗索土狼',
    'Darkfuse Inspector': '暗索调查员',
    'Darkfuse Jumpstarter': '暗索接线者',
    'Darkfuse Mechadrone': '暗索无人机',
    'Darkfuse Soldier': '暗索士兵',
    'Deathwalker': '死亡行者',
    'Defense Bot Mk I': '防御机器人MkI型',
    'Defense Bot Mk III': '防御机器人MkIII型',
    'Demolition Duo': '破拆双人组',
    'Dessia the Decapitator': '斩首者德茜雅',
    'Devout Priest': '虔诚的牧师',
    'Diseased Horror': '染病恐魔',
    'Disgusting Refuse': '恶心的残躯',
    'Disturbed Kelp': '被惊扰的海藻',
    'Dokigg the Brutalizer': '残暴者多基格',
    'Dynamite Mine Cart': '炸药采矿车',
    'Earthrager': '地怒者',
    'Elaena Emberlanz': '艾蕾娜·安博兰兹',
    'Fanatical Conjuror': '狂热的咒术师',
    'Fervent Sharpshooter': '热诚的神射手',
    'Flavor Scientist': '风味科学家',
    'Footbomb Hooligan': '足球炸弹流氓',
    'Forge Master Damian': '铸炉大师达米安',
    'G.U.A.R.D.': 'G.U.A.R.D.型护卫狼',
    'Galvazzt': '加瓦兹特',
    'Geezle Gigazap': '吉泽尔·超震',
    'Gnomercy 4.U.': '仁慈侏儒4.U.型',
    'Goldie Baronbottom': '戈尔迪·底爵',
    'Gorechop': '斩血',
    'Guard Captain Suleyman': '守卫队长苏雷曼',
    'Harugia the Bloodthirsty': '嗜血的哈鲁吉亚',
    'Head Machinist Sparkflux': '首席机械师闪流',
    'Heavin the Breaker': '粉碎者赫文',
    'High Priest Aemya': '高阶牧师艾姆雅',
    'Hired Assassin': '雇来的刺客',
    'Hired Muscle': '雇佣的打手',
    "I'pa": '艾帕',
    'Inconspicuous Plant': '不起眼的盆栽',
    'Junkyard D.0.G.': 'D.0.G.型垃圾场巡犬',
    'K.U.-J.0.': '狂犬K.U.-J.0.',
    'Keeza Quickfuse': '齐扎·迅索',
    'Keeza Quickfuse and Bront': '破拆双人组',
    'King Mechagon': '麦卡贡国王',
    "Kings' Rest": '诸王之眠',
    'Kobold Flametender': '狗头人护焰者',
    'Kobold Taskworker': '狗头人履职者',
    "Kul'tharok": '库尔萨洛克',
    'Kyrioss': '凯里欧斯',
    'Kystia Manaheart': '凯斯媞亚·魔力之心',
    'Leaping Spark': '跃动火花',
    'Lightspawn': '光耀之子',
    'Lithiel Cinderfury': '利希尔·烬怒',
    'Living Waste': '活体废料',
    'Loaderbot': '载货机器人',
    'Lost Soul': '失落的灵魂',
    'Lowly Moleherd': '低贱的鼹鼠倌',
    "Machinist's Garden": '机械师的花园',
    'Maniacal Soulbinder': '狂热的缚魂者',
    'Mech Jockey': '机甲驾驶员',
    'Mechadrone Sniper': '无人机狙击手',
    'Mechagon Mechanic': '麦卡贡机械师',
    'Mechagon Tinkerer': '麦卡贡工匠',
    'Mechanized Peacekeeper': '机械化维和者',
    'Menial Laborer': '卑微的劳工',
    'Merektha': '米利克萨',
    'Metal Gunk': '金属黏泥',
    'Mine Rat': '矿井鼠',
    'Mogul Razdunk': '商业大亨拉兹敦克',
    'Mordretha, the Endless Empress': '无尽女皇莫德蕾莎',
    'Murder Row': '密谋小径',
    'Nefarious Darkspeaker': '卑劣的暗语者',
    'Nekthara the Mangler': '裂伤者耐克萨拉',
    'Off-Duty Laborer': '下班的劳工',
    "Ol' Waxbeard": '老蜡须',
    'Omega Buster': '欧米茄破坏者',
    'Oozing Leftovers': '渗漏的残躯',
    'Oppressive Banner': '压制战旗',
    'Ordnance Specialist': '军械专家',
    'Ossified Conscript': '骨化的援兵',
    'Paceran the Virulent': '疫毒者巴瑟兰',
    'Pack Mole': '运货鼹鼠',
    'Portal Guardian': '传送门守卫',
    'Prioress Murrpray': '隐修院长穆普雷',
    'Putrid Butcher': '腥臭屠夫',
    'Quartermaster Koratite': '军需官科拉泰特',
    'Raging Bloodhorn': '狂怒的血角',
    'Rancid Gasbag': '腐臭的气囊怪',
    'Rank Overseer': '职阶监督者',
    'Ravenous Cinderbee': '贪婪的燧烬蜂',
    'Refreshment Vendor': '零食商贩',
    'Rek the Hardened': '老练的里克',
    'Risen Footman': '复活的步兵',
    'Risen Mage': '亡灵法师',
    'Rixxa Fluxflame': '瑞克莎·流火',
    'Rocket Tonk': '火箭坦克',
    'Royal Jelly Purveyor': '蜂王浆供应商',
    'Royal Wicklighter': '皇家点芯者',
    'Ruby Life Pools': '红玉新生法池',
    'Safety Shark': '护卫鲨鱼',
    'Sathel the Accursed': '受诅者赛泽尔',
    'Scaffolding': '脚手架',
    'Sergeant Shaynemail': '歇尼麦尔中士',
    'Shackled Soul': '桎梏之魂',
    'Shalebiter': '页岩啃噬者',
    'Shambling Arbalest': '蹒跚的弩手',
    'Shreddinator 3000': '撕碎王3000型',
    'Shuffling Horror': '残步恐魔',
    'Sir Braunpyke': '布朗派克爵士',
    'Skittering Darkness': '掠行之暗',
    'Sootsnout': '灰鼻',
    'Soulforged Bonereaver': '魂铸白骨编织者',
    'Spider Tank': '蜘蛛坦克',
    'Stonefury': '巨石之怒',
    'Stormguard Gorren': '雷卫戈伦',
    'Stormrider Vokmar': '驭雷者沃克玛尔',
    'Strider Tonk': '陆行鸟坦克',
    'Swampface': '沼面',
    'Taener Duelmal': '泰纳·杜尔玛',
    'Taskmaster Askari': '监工阿斯加里',
    'Taste Tester': '美味测试员',
    'Tasting Room Attendant': '品酒间侍从',
    'Temple of Sethraliss': '塞塔里斯神庙',
    'Test Subject': '测试对象',
    'The Blinding Vale': '夺目谷',
    'The Candle King': '蜡烛之王',
    'The Darkness': '黑暗之主',
    'The Dawnbreaker': '破晨号',
    'The Platinum Pummeler': '白金拳手',
    'The Stonevault': '矶石宝库',
    'Ticking Time Bomb': '定时炸弹',
    'Torchsnarl': '炬龇',
    'Tussle Tonks': '角力坦克',
    'Undercrawler': '幽暗爬行者',
    'Unruly Stormrook': '任性的雷鸫',
    'Unyielding Contender': '不屈的参赛者',
    'Venture Co. Alchemist': '风险投资公司炼金师',
    'Venture Co. Architect': '风险投资公司建筑师',
    'Venture Co. Contractor': '风险投资公司合同工',
    'Venture Co. Diver': '风险管理公司潜水员',
    'Venture Co. Earthshaper': '风险投资公司塑地者',
    'Venture Co. Electrician': '风险投资公司电工',
    'Venture Co. Honey Harvester': '风险投资公司蜂蜜收割者',
    'Venture Co. Mastermind': '风险投资公司策划',
    'Venture Co. Patron': '风险投资公司主顾',
    'Venture Co. Pyromaniac': '风险投资公司纵火狂',
    'Venture Co. Skyscorcher': '风险投资公司灼天者',
    'Venture Co. Surveyor': '风险投资公司勘探员',
    'Venture Co. War Machine': '风险投资公司战争机器',
    'Void Ascendant': '虚空晋升者',
    'Void-Cursed Crusher': '虚咒碾压者',
    'Voidrider': '驭虚者',
    'Voidstone Awakened': '觉醒的虚空石',
    'Voidstone Monstrosity': '虚空石畸体',
    'Wandering Candle': '漫游蜡烛',
    'Wanton Sapper': '暴虐的工兵',
    'War Lynx': '作战山猫',
    'Waste Processing Unit': '废料处理单位',
    'Waterworks Crocolisk': '水能堡鳄鱼',
    'Weapons Tester': '武器测试员',
    'Worker Bee': '工蜂',
    'Workshop Defender': '车间防御者',
    'Wriggling Darkspawn': '蠕动暗嗣',
    'Xathuux the Annihilator': '歼灭者萨祖克斯',
    'Xav the Unfallen': '无堕者哈夫',
    'Yes Man': '好好先生',
    'Zaen Bladesorrow': '赞恩·刃悲',
    'Zealous Templar': '热心的圣殿骑士',
}

SPEC_NAMES = {
    "DeathKnight-Blood": "鲜血死亡骑士",
    "DeathKnight-Frost": "冰霜死亡骑士",
    "DeathKnight-Unholy": "邪恶死亡骑士",
    "DemonHunter-Havoc": "浩劫恶魔猎手",
    "DemonHunter-Vengeance": "复仇恶魔猎手",
    "Druid-Balance": "平衡德鲁伊",
    "Druid-Feral": "野性德鲁伊",
    "Druid-Guardian": "守护德鲁伊",
    "Druid-Restoration": "恢复德鲁伊",
    "Evoker-Augmentation": "增辉唤魔师",
    "Evoker-Devastation": "湮灭唤魔师",
    "Evoker-Preservation": "恩护唤魔师",
    "Hunter-BeastMastery": "野兽控制猎人",
    "Hunter-Marksmanship": "射击猎人",
    "Hunter-Survival": "生存猎人",
    "Mage-Arcane": "奥术法师",
    "Mage-Fire": "火焰法师",
    "Mage-Frost": "冰霜法师",
    "Monk-Brewmaster": "酒仙武僧",
    "Monk-Mistweaver": "织雾武僧",
    "Monk-Windwalker": "踏风武僧",
    "Paladin-Holy": "神圣圣骑士",
    "Paladin-Protection": "防护圣骑士",
    "Paladin-Retribution": "惩戒圣骑士",
    "Priest-Discipline": "戒律牧师",
    "Priest-Holy": "神圣牧师",
    "Priest-Shadow": "暗影牧师",
    "Rogue-Assassination": "奇袭潜行者",
    "Rogue-Outlaw": "狂徒潜行者",
    "Rogue-Subtlety": "敏锐潜行者",
    "Shaman-Elemental": "元素萨满",
    "Shaman-Enhancement": "增强萨满",
    "Shaman-Restoration": "恢复萨满",
    "Warlock-Affliction": "痛苦术士",
    "Warlock-Demonology": "恶魔学识术士",
    "Warlock-Destruction": "毁灭术士",
    "Warrior-Arms": "武器战士",
    "Warrior-Fury": "狂怒战士",
    "Warrior-Protection": "防护战士",
}

CLASS_NAMES = {
    "DeathKnight": "死亡骑士",
    "DemonHunter": "恶魔猎手",
    "Druid": "德鲁伊",
    "Evoker": "唤魔师",
    "Hunter": "猎人",
    "Mage": "法师",
    "Monk": "武僧",
    "Paladin": "圣骑士",
    "Priest": "牧师",
    "Rogue": "潜行者",
    "Shaman": "萨满",
    "Warlock": "术士",
    "Warrior": "战士",
}


@dataclass(frozen=True)
class PhaseTransition:
    id: int
    start_time: float


@dataclass(frozen=True)
class DungeonPull:
    """大秘 / 地下城整场 fight 内的一次 pull（相对报告起点的时间戳）。"""

    id: int
    name: str
    encounter_id: int
    start_time: float
    end_time: float
    kill: bool | None = None

    @property
    def duration_ms(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    @property
    def is_boss(self) -> bool:
        return self.encounter_id != 0


@dataclass(frozen=True)
class Fight:
    id: int
    name: str
    encounter_id: int
    difficulty: int | None
    kill: bool | None
    start_time: float
    end_time: float
    fight_percentage: float | None
    boss_percentage: float | None
    size: int | None
    average_item_level: float | None
    last_phase: int | None
    in_progress: bool
    keystone_level: int | None
    phase_transitions: tuple[PhaseTransition, ...] = ()
    dungeon_pulls: tuple[DungeonPull, ...] = ()

    @property
    def duration_ms(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    @property
    def is_boss(self) -> bool:
        return self.encounter_id != 0


@dataclass(frozen=True)
class Report:
    code: str
    title: str
    start_time: float
    end_time: float
    owner: str | None
    zone_name: str | None
    fights: tuple[Fight, ...]

    @property
    def boss_fights(self) -> tuple[Fight, ...]:
        return tuple(fight for fight in self.fights if fight.is_boss and not fight.in_progress)


@dataclass(frozen=True)
class PlayerRow:
    name: str
    spec: str
    total: int
    per_second: float
    active_per_second: float | None
    overheal_percent: float | None
    top_ability: str | None


@dataclass(frozen=True)
class DeathEvent:
    name: str
    spec: str
    offset_ms: float
    ability: str | None


@dataclass(frozen=True)
class FightAnalysis:
    fight: Fight
    damage: tuple[PlayerRow, ...]
    healing: tuple[PlayerRow, ...]
    damage_taken: tuple[PlayerRow, ...]
    deaths: tuple[DeathEvent, ...]


@dataclass(frozen=True)
class BossSummary:
    name: str
    encounter_id: int
    difficulty: int | None
    keystone_level: int | None
    attempts: int
    kills: int
    fastest_kill_ms: float | None
    best_wipe: Fight | None
    fights: tuple[Fight, ...]


@dataclass(frozen=True)
class ActorInfo:
    id: int
    name: str
    type: str
    sub_type: str | None
    pet_owner: int | None = None
    server: str | None = None

    @property
    def is_player(self) -> bool:
        # table 条目常用职业作 type；masterData 则为 type=Player、subType=职业
        return self.type == "Player" or self.type in PLAYER_CLASSES

    @property
    def is_pet(self) -> bool:
        return self.type == "Pet"

    @property
    def is_npc(self) -> bool:
        return self.type in {"NPC", "Boss"}

    @property
    def is_boss_npc(self) -> bool:
        return self.sub_type == "Boss" or self.type == "Boss"

    @property
    def player_class(self) -> str | None:
        if self.type in PLAYER_CLASSES:
            return self.type
        if self.type == "Player" and self.sub_type in PLAYER_CLASSES:
            return self.sub_type
        return None


@dataclass(frozen=True)
class TimelineEvent:
    offset_ms: float
    kind: str  # boss / defense / phase
    ability: str
    ability_id: int | None = None
    category: str | None = None
    actor: str | None = None
    spec: str | None = None
    # WCL 职业 slug，如 Mage / Warrior；用于颜色与职业图标
    actor_class: str | None = None
    icon: str | None = None
    ability_en: str | None = None
    target: str | None = None
    # 首领施法：begincast→cast 的施法/引导时长；瞬发为 0
    duration_ms: float = 0.0
    # Wowhead 技能说明 / 施法时间（瞬发或读条）/ 效果持续
    description: str | None = None
    cast_label: str | None = None
    duration_label: str | None = None


@dataclass(frozen=True)
class BossAbilityCd:
    """本场同一首领技能的施法间隔摘要（表观 CD，未必等于真实冷却）。"""

    ability_id: int | None
    ability: str
    cast_count: int
    timestamps_ms: tuple[float, ...]
    intervals_ms: tuple[float, ...]
    median_interval_ms: float | None
    min_interval_ms: float | None
    max_interval_ms: float | None
    ability_en: str | None = None
    icon: str | None = None


@dataclass(frozen=True)
class HealthSample:
    """某一时刻敌方单位血量采样（战斗相对 offset）。"""

    offset_ms: float
    pct: float
    current: float | None = None
    max_hp: float | None = None


@dataclass(frozen=True)
class HealthSeries:
    """单个首领 / 小怪的血量时间序列。"""

    id: int
    name: str
    is_boss: bool
    instance: int = 0
    samples: tuple[HealthSample, ...] = ()


@dataclass(frozen=True)
class TimelineAnalysis:
    fight: Fight
    events: tuple[TimelineEvent, ...]
    boss_cds: tuple[BossAbilityCd, ...] = ()
    health_series: tuple[HealthSeries, ...] = ()


def difficulty_label(difficulty: int | None, keystone_level: int | None = None) -> str:
    if difficulty is None:
        return "未知"
    name = DIFFICULTY_NAMES.get(difficulty, f"难度 {difficulty}")
    if difficulty == 10 and keystone_level:
        return f"{name} +{keystone_level}"
    return name


def localized_encounter_name(name: str) -> str:
    """展示用名称：有中文别名时优先，并保留英文以便对照 WCL 英文 API。"""
    zh = FIGHT_NAME_ZH.get(name)
    if zh and zh != name:
        return f"{zh}（{name}）"
    return name


def short_encounter_name(name: str) -> str:
    """按钮 / 紧凑 UI：有中文别名只用中文，否则原文。"""
    return FIGHT_NAME_ZH.get(name) or name


def fight_display_name(fight: Fight) -> str:
    return localized_encounter_name(fight.name)


def fight_kind_label(fight: Fight) -> str:
    if fight.keystone_level or fight.difficulty == 10:
        return "大秘境"
    if fight.is_boss:
        return "团本/首领"
    return "小怪"


def spec_label(icon: str | None, actor_type: str | None) -> str:
    if icon and icon in SPEC_NAMES:
        return SPEC_NAMES[icon]
    if actor_type and actor_type in CLASS_NAMES:
        return CLASS_NAMES[actor_type]
    if icon and "-" in icon:
        return icon.replace("-", " ")
    return actor_type or icon or "未知"


def is_player(entry: dict) -> bool:
    return entry.get("type") in PLAYER_CLASSES
