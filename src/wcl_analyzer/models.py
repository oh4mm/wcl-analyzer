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
    # 塞塔里斯神庙小怪 / 召唤物（本场 JR9… 等日志补全，Wowhead CN）
    'A Knot of Snakes': '缠绕的蛇群',
    'Agitated Nimbus': '暴怒云气',
    'Barbed Krolusk': '倒刺三叶虫',
    'Brood Tender': '育巢者',
    'Corrupted Guardian': '堕落的守护者',
    'Dutiful Tamer': '尽职的驯兽师',
    'Egg': '卵',
    'Essence Defiler': '精华污染者',
    'Eye of Sethraliss': '塞塔里斯之眼',
    'Faithless Conscript': '无信援兵',
    'Faithless Subjugator': '无信征服者',
    'Faithless Tormentor': '无信折磨者',
    'Imbued Stormcaller': '灌注能量的唤雷者',
    'Krolusk Matriarch': '三叶虫主母',
    'Lesser Lifeforce': '次级生命之力',
    'Lifeforce': '生命之力',
    'Lightning Serpent': '闪电毒蛇',
    'Lightning Spire': '闪电尖塔',
    'Loose Spark': '不羁的火花',
    'Orb Watcher': '宝珠守望者',
    'Poisonous Viper': '剧毒蝰蛇',
    'Polarized Spire': '极化尖塔',
    'Rogue Krolusk': '游荡三叶虫',
    'Sand-Sworn Rider': '砂誓骑兵',
    'Sandfury Stonefist': '沙怒石拳战士',
    'Sandswept Hunter': '流沙猎手',
    'Shrouded Fang': '隐秘之牙',
    'Snake': '蛇',
    'Solid Egg': '坚固的卵',
    'Spark Channeler': '火花引导者',
    'Static Anomaly': '静电异常体',
    'Storm Adept': '风暴能手',
    'Storm Serpent': '风暴飞蛇',
    'Swarming Krolusk': '群聚三叶虫',
    'Temple Disruptor': '神庙干扰者',
    'Toxic Viper': '剧毒蝰蛇',
    'Twisted Hexxer': '扭曲的妖术师',
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
    # —— Midnight 赛季 MDT 副本 / NPC（Locales/zhCN.lua）——
    # WCL fight.name 常用带空格写法（MDT key 多为 CamelCase）
    "Algeth'ar Academy": '艾杰斯亚学院',
    'Altar of Fangs': '毒牙祭坛',
    'Den of Nalorakk': '纳洛拉克的洞穴',
    "Magister's Terrace": '魔导师平台',
    'Maisara Caverns': '迈萨拉洞窟',
    'Nexus Point Xenas': '节点希纳斯',
    'Nexus-Point Xenas': '节点希纳斯',
    'Pit of Saron': '萨隆矿坑',
    'Voidscar Arena': '虚空之痕竞技场',
    'Windrunner Spire': '风行者之塔',
    'Abducted Drakonid': '被绑架的龙人',
    'Adept of the Dawn': '黎明精锐',
    'Adorned Bladetalon': '华胄锐爪战士',
    'Aegyra the Unyielding': '不屈的埃吉拉',
    'Aggravated Skitterfly': '被激怒的掠蜓',
    'Agitated Voidscythe': '焦躁的虚镰',
    "Aka'ali the Conqueror": '征服者阿卡阿里',
    "Algeth'ar Echoknight": '艾杰斯亚回声骑士',
    'AlgetharAcademy': '艾杰斯亚学院',
    'Alpha Eagle': '头领鹰隼',
    'AltarOfFangs': '毒牙祭坛',
    'Angry Krolusk': '暴怒的三叶虫',
    'Animated Codex': '活化魔典',
    'Animated Gold': '活性黄金',
    'Animated Guardian': '活化守卫',
    'Apex Lynx': '山猫首领',
    'Arakkoa Magnifying Glass': '鸦人放大镜',
    'Araknath': '阿拉卡纳斯',
    'Arcane Forager': '奥术抢劫者',
    'Arcane Magister': '奥术魔导师',
    'Arcane Sentry': '奥术哨兵',
    'Arcanist Cadaver': '奥术师遗骸',
    'Arcanotron Custos': '奥能金刚库斯托斯',
    'Ardent Cutthroat': '狂热割喉者',
    'Ascendant Serpent': '晋升之蛇',
    'Ashseer Flamelasher': '灰烬先知烈焰鞭笞者',
    'Atroxus': '阿特洛苏斯',
    'Avatar of Determination': '决意化身',
    'Barrel of Apples': '苹果桶',
    'Belath Dawnblade': '贝拉斯·黎明之刃',
    'Berry Bush': '莓果灌木丛',
    'Blade of the Altar': '祭坛利刃',
    'Blazebound Destroyer': '炎缚毁灭者',
    'Blazebound Firestorm': '炎缚火焰风暴',
    'Blazing Pyromancer': '炽热炎术士',
    'Blinding Sun Priestess': '耀目太阳祭司',
    'Blistercreep': '爆爬虫',
    'Bloated Lasher': '臃肿的鞭笞者',
    'Bloodletter': '放血者',
    'Bloodsworn Assassin': '血誓刺客',
    'Bloodthorn Roots': '血棘之根',
    'Bonded Beasttamer': '羁绊驯兽师',
    'Bound Defender': '被缚的防御者',
    'Bound Voidcaller': '被束缚的虚空召唤者',
    'Bramblemaw Bear': '荆喉熊',
    'Bribed Captain': '受贿的队长',
    'Bribed Guard': '被买通的守卫',
    'Brightscale Wyrm': '亮鳞浮龙',
    'Broken Pipe': '断裂的管道',
    'Brutal Overseer': '鲁莽监督者',
    'Brutok': '布鲁托克',
    'Captive': '俘虏',
    'Celestial Drifter': '天界漂流者',
    'Charonus': '煞戎努斯',
    'Chitigoth': '几丁高斯',
    'Circuit Seer': '回路先知',
    'Coalesced Void': '凝结虚空',
    'Coffin': '棺材',
    'Commander Kroluk': '指挥官克罗鲁科',
    'Core Technician': '核心技师',
    'Corespark Conduit': '核闪导体',
    'Corespark Pylon': '核闪晶塔',
    'Corewarden Nysarra': '核心守卫奈萨拉',
    'Corewright Arcanist': '核技奥术师',
    'Corrupted Manafiend': '被腐化的嗜魔者',
    'Corrupted Warlock': '腐化的术士',
    'Crate Loader': '装箱工',
    'Crawth': '克罗兹',
    'Creeping Spindleweb': '潜伏的纺丝蜘蛛',
    'Curious Yearling': '好奇的幼崽',
    'Cursed Voidcaller': '受诅的虚空召唤者',
    'Dark Conjurer': '黑暗咒术师',
    'Darkfang': '黯牙',
    "Death's Grasp": '死亡之握',
    'Deathwhisper Necrolyte': '亡语者侍僧',
    'Deepstone Earthshaper': '深石塑地者',
    'Defier Draghar': '亵渎者德拉加尔',
    'Defiled Golem': '亵渎傀儡',
    'Degentrius': '迪詹崔乌斯',
    'Demon Fly': '魔蝇',
    'DenOfNalorakk': '纳洛拉克的洞穴',
    'Depravation Wave Stalker': '堕落之波追踪者',
    'Devoted Woebringer': '虔诚的哀难使者',
    'Devouring Brutalizer': '贪噬残虐者',
    'Devouring Tyrant': '吞噬暴君',
    'Dire Voidbender': '恐怖缚灵师',
    'Dominated Brawler': '被统御的斗士',
    'Dread Raven': '恐惧渡鸦',
    'Dread Souleater': '恐怖食魂者',
    'Dreadflail': '恐惧连枷',
    'Dreadful Voidwalker': '恐怖的虚空行者',
    'Dreadpulse Lich': '恐惧脉冲巫妖',
    'Driving Gale-Caller': '强势唤风者',
    'Duskfright Herald': '暮恐传令官',
    'Dutiful Groundskeeper': '尽责的场地管理员',
    'Earthbound Guardian': '缚地守护者',
    'Earthwhisper Tender': '地语看护者',
    'Echo of Doragosa': '多拉苟萨的回响',
    'Echo of Nalorakk': '纳洛拉克的回响',
    'Embalming Fluid': '防腐液',
    'Emberdawn': '烬晓',
    'Enthralled Shaman': '被奴役的萨满',
    'Erkhart Stormvein': '厄克哈特·风脉',
    'Ethereal Shade': '虚灵之影',
    'Explosive Totem': '爆裂图腾',
    'Famished Broken': '饥饿的破碎者',
    'Fel Invoker': '邪能祈求者',
    'Felmaster Lucsei': '邪能主宰鲁科西',
    'Felonious Mage': '凶邪的法师',
    'Felwyrm': '邪能浮龙',
    'Feral Saberon': '狂野的刃牙虎人',
    'Fervent Apothecary': '热诚的药剂师',
    'Flamegullet': '烈焰之咽',
    'Flaming Updraft': '炽焰腾流',
    'Flarebat': '耀光蝠',
    'Flashfrost Chillweaver': '闪霜织寒者',
    'Flesh Behemoth': '血肉巨兽',
    'Flux Engineer': '通量工程师',
    'Forbidden Freight': '违禁的货物',
    'Forgemaster Garfrost': '熔炉之主加弗斯特',
    'Fractured Image': '分裂镜像',
    'Fractured Shivercore': '碎裂的震颤核心',
    'Frenzied Berserker': '躁乱的狂战士',
    'Frigid Mauler': '酷寒重殴者',
    'Frostfang': '霜牙',
    'Furious Vilefiend': '狂怒的邪犬',
    'Gemellus': '吉美尔鲁斯',
    'Ghostly Brute': '鬼魂蛮兵',
    'Glacial Revenant': '冰川亡魂',
    'Glacieth': '冰煞',
    'Gloombound Shadebringer': '幽缚唤影者',
    'Gloomwing Bat': '晦翼蝙蝠',
    'Grand Nullifier': '大废止者',
    'Grand Shadow-Weaver': '大织影者',
    'Gravitic Orb': '引力宝珠',
    'Grim Skirmisher': '阴冷散兵',
    'Grizzled Warbringer': '老练的战争使者',
    'Guard Captain Atu': '守卫队长阿图',
    'Guardian Sentry': '守护者哨兵',
    'Half-Finished Mummy': '未完成的木乃伊',
    'Hatchling': '幼体',
    'Haunting Grunt': '恼人的步兵',
    'Healing Tide Totem': '治疗之潮图腾',
    'Hex Guardian': '妖术守护者',
    'Hexbound Eagle': '妖缚飞鹰',
    'High Channeler Ryvati': '大引导者莱瓦迪',
    'High Evolutionist': '高阶进化者',
    'High Sage Viryx': '高阶贤者维里克斯',
    'Hollow Soulrender': '空洞的裂魂者',
    'Hollowsoul Scrounger': '虚隐之魂搜寻者',
    'Hollowsoul Shredder': '虚隐之魂撕裂者',
    'Honored Raptor': '荣耀迅猛龙',
    'Hulking Juggernaut': '魁梧主宰',
    'Hungry Lasher': '饥饿的鞭笞者',
    'Iceborn Proto-Drake': '冰魂始祖龙',
    'Ick': '伊克',
    'Ikuzz the Light Hunter': '圣光猎手伊库兹',
    'Infernal': '地狱火',
    'Influentual Reviewer': '走红的评论家',
    'Infused Eggs': '注能之卵',
    'Infused Whelp': '注能龙崽',
    'Initiate of the Rising Sun': '旭日新兵',
    'Interment Construct': '葬礼构造体',
    'Kalis': '卡莉斯',
    'Kasreth': '卡斯雷瑟',
    'Keen Headhunter': '敏锐的猎头者',
    'Keen Taskmaster': '敏锐的监工',
    'Keen-Eyed Striker': '锐眼掠击鹰',
    'Kezkitt': '科兹齐特',
    'Kilivore Screamer': '千噬兽尖啸者',
    "King A'akul": '阿库尔大王',
    'King Dazar': '达萨大王',
    "King Rahu'ai": '拉胡艾大王',
    'King Timalji': '提玛吉大王',
    'Kokia Blazehoof': '柯姬雅·焰蹄',
    'Krick': '科瑞克',
    'Kula the Butcher': '屠夫库拉',
    'Kyrakka': '基拉卡',
    'Kyrakka and Erkhart Stormvein': '基拉卡和厄克哈特·风脉',
    "L'ura": '鲁拉',
    'Lasher': '鞭笞者',
    'Latch': '拉奇',
    'Leafy Grovecrawler': '多叶林莽爬行者',
    'Leaping Geist': '腾跃的恶鬼',
    'Legion Axe': '军团大斧',
    'Lekshi': '莱克希',
    'Lightblossom': '光明之花',
    'Lightblossom Trinity': '光明之花三杰',
    'Lightfeather Petalwing': '光羽瓣翼鸟',
    'Lightgorged Lasher': '光噬鞭笞者',
    'Lightspawn Lasher': '光诞鞭笞者',
    'Lightward Healer': '护光者医疗师',
    'Lightwarden Ruia': '护光者鲁伊亚',
    'Lightwrought': '光诞',
    'Lingering Image': '残存镜像',
    'Lingering Marauder': '徘徊的掠夺者',
    'Living Venom': '活体毒液',
    'Loa Speaker Nanea': '神灵代言人纳尼亚',
    'Longtooth Tuskarr': '长牙海象人',
    'Lost Sethrak': '迷失的蛇人',
    'Lothraxion': '洛萨克森',
    'Lowborn Servant': '下层仆从',
    'Loyal Saberfang': '忠诚的刃牙山猫',
    'Loyal Worg': '忠诚的座狼',
    'Lumbering Plaguehorror': '笨拙的灾疫恐魔',
    'Luminous Thornmaw': '发光的棘喉兽',
    'MagistersTerrace': '魔导师平台',
    'Magma Totem': '熔岩图腾',
    'MaisaraCaverns': '迈萨拉洞窟',
    'Mana Battery': '法力电池',
    'Masked Noble': '蒙面贵族',
    'Massive Felwyrm': '巨大的邪能浮龙',
    'Mchimba the Embalmer': '殓尸者姆沁巴',
    'Meittik': '梅提克',
    'Melidrussa Chillworn': '梅莉杜莎·寒妆',
    'Merciless Subjugator': '残忍征服者',
    'Minion of Zul': '祖尔的爪牙',
    'Mire Laborer': '泥潭劳工',
    'MurderRow': '密谋小径',
    "Muro'jin": '姆罗金',
    'Nalorakk': '纳洛拉克',
    'Nauseous Patron': '作呕的主顾',
    'Nekraxx': '内克拉克斯',
    'Newborn Potadpole': '新生的薯身幼蟾',
    'Nexus Adept': '节点专家',
    'NexusPointXenas': '节点希纳斯',
    'Nibbles': '咬咬',
    'Null Sentinel': '虚无哨兵',
    'Nullifier': '废止者',
    'Outcast Warrior': '流亡战士',
    'Overgrown Ancient': '茂林古树',
    'Overgrown Hydra': '长得过大的多头花',
    'Pesty Lashling': '烦人的鞭笞菇幼苗',
    'Phalanx Breaker': '破阵铁骑',
    'Phantasmal Mystic': '幻形秘术师',
    'Phantom Hex Priest': '幻影妖术祭司',
    'PitOfSaron': '萨隆矿坑',
    'Plungetalon Gargoyle': '落爪石像鬼',
    'Potadpole Egg': '薯身幼蟾卵',
    'Potatoad Matriarch': '薯身蟾主母',
    'Primal Juggernaut': '原始主宰',
    'Primal Serpent': '原始毒蛇',
    'Primal Thundercloud': '原始雷云',
    'Primalist Cinderweaver': '拜荒织烬者',
    'Protective Turtle': '充满保护欲的乌龟',
    'Purification Construct': '净化构造体',
    'Quarry Tormentor': '采掘场折磨者',
    'Queen Patlaa': '帕特拉女王',
    'Queen Wasi': '沃希女王',
    'Radiant Spellsower': '光耀播法者',
    'Radiant Swarm': '光耀虫群',
    'Raging Raptor': '暴怒的迅猛龙',
    'Raging Squall': '狂怒的飑风',
    "Raj'kess the Spellstorm": '法术风暴拉杰克斯',
    "Rak'tul": '拉克图尔',
    'Ranjit': '兰吉特',
    'Rattling Writhe': '振响的扭缠蛇',
    "Rav'i": '拉维',
    'Ravenous Descendant': '贪婪的后裔',
    'Ravenous Umbralfin': '贪食的影鳍鳐',
    'Reanimated Warrior': '复活的战士',
    'Reban': '莱班',
    'Reformed Voidling': '重塑的虚空之子',
    'Restless Gnarldin': '不安的纳拉丁',
    'Restless Heart': '无眠之心',
    'Restless Steward': '焦躁的管家',
    'Rift Warden': '裂隙守护者',
    'Rimebone Coldwraith': '霜骨冰骸',
    'Rimefang': '霜牙',
    'Risen Hexer': '复活的妖术师',
    'Risen Soldier': '复活的士兵',
    'Ritual Chieftain': '仪式首领',
    'Ritual Hexxer': '仪式妖术师',
    'Ritual Snake': '仪式毒蛇',
    'Ritual Spirit': '仪式精魂',
    "Rokh'zal": '洛克扎尔',
    'Rotling': '腐尸',
    'Rotting Ghoul': '腐烂的食尸鬼',
    'Row Hooligan': '径巷流氓',
    'Rowdy Patron': '吵闹的主顾',
    'Royal Berserker': '皇家狂战士',
    'RubyLifePools': '红玉新生法池',
    'Ruinous Stormbringer': '毁灭唤风者',
    'Rukhran': '鲁克兰',
    'Runed Spellbreaker': '符文破法者',
    'Ruthless Riftstalker': '无情的裂隙猎手',
    'Ruthless Totemcaller': '冷酷的图腾召唤者',
    'Salmon Pool': '鲑鱼池',
    'Sandswept Marksman': '卷沙神射手',
    'Saprish': '萨普瑞什',
    'Savage Shredclaw': '野蛮裂爪兽',
    'Scavenging Siphoid': '食腐虹虚魔',
    'Scorchling': '灼烧元素',
    'Scourge Plaguespreader': '天灾瘟疫传播者',
    'Scourgelord Tyrannus': '天灾领主泰兰努斯',
    'Scouting Trapper': '侦察诱捕者',
    'Seat of the Triumvirate': '执政团之座',
    'Seductive Sayaad': '诱惑的萨亚德',
    'Selenar Sunshy': '赛勒纳·避日',
    "Seneschal M'bara": '总管姆巴拉',
    'Sentinel of Winter': '寒冬哨兵',
    'Seranel Sunlash': '瑟拉奈尔·日鞭',
    'Shade of Krick': '科瑞克之影',
    'Shadewing': '影翼鳐',
    'Shadow of Zul': '祖尔之影',
    'Shadow-Borne Champion': '影裔勇士',
    'Shadowguard Champion': '影卫勇士',
    'Shadowguard Defender': '影卫防御者',
    'Shadowrift Voidcaller': '影卫虚空召唤师',
    'Shivan Punisher': '破坏魔惩罚者',
    'Silvermoon Patron': '银月城主顾',
    'Skeletal Hunting Raptor': '骸骨狩猎迅猛龙',
    'Skyreach': '通天峰',
    'Skyreach Sun Construct Prototype': '通天峰炎阳构装体雏形',
    'Smudge': '黑泥',
    'Snitch %d Interrogated': '告密者%d已审问',
    'Snow Orb Stalker': '冰雪之珠追踪者',
    'Soaring Chakram Master': '飞天轮舞大师',
    'Solar Construct': '烈日构装体',
    'Solar Elemental': '太阳元素',
    'Solar Orb': '太阳宝珠',
    'Soulbind Totem': '缚魂图腾',
    'Spectral Axethrower': '幻影掷斧者',
    'Spectral Invoker': '幽魂唤魔师',
    'Spectral Shaman': '幻影萨满祭司',
    'Spellbound Battleaxe': '缚法战斧',
    'Spellguard Magus': '护法魔导师',
    'Spellwoven Familiar': '魔网编织魔宠',
    'Spindleweb Hatchling': '纺丝蜘蛛幼体',
    'Spineshield Beetle': '脊盾甲虫',
    'Spirit Bear': '幽灵熊',
    'Spirit Moonkin': '幽灵枭兽',
    'Spirit of Hunger': '饥渴之灵',
    'Sporeblight Belcher': '孢荒喷射者',
    'Starvation Effigy': '饥荒雕像',
    'Storm Warrior': '风暴战士',
    'Stormbound Mystic': '雷缚秘法师',
    'Street Sneak': '街头扒手',
    'Sunblade Enforcer': '炎刃执行者',
    'Suntalon': '日爪',
    'Suntalon Tamer': '日爪驯服者',
    'Sunwing': '日翼幼雏',
    'Swiftshot Archer': '迅捷弓箭手',
    'Sycophantic Tarasek': '谄媚的塔拉赛',
    "T'zala": '提扎拉',
    'Targeting Stalker': '指向追踪者',
    "Taz'Rah": '塔兹拉尔',
    'Tempest Channeler': '暴风引导者',
    'Terra Rumbler': '撼地奔行者',
    'Territorial Dragonhawk': '领地龙鹰',
    'Territorial Eagle': '领地鹰隼',
    'Territorial Matriarch': '领地主母',
    'The Golden Serpent': '黄金风蛇',
    'The Hoardmonger': '囤宝狂人',
    'The Pale Eye': '苍白之眼',
    'The Winter Squall': '寒冬暴风雪',
    'The Writhing Coil': '扭缠盘蛇',
    'TheBlindingVale': '夺目谷',
    'Thornclaw Gatherer': '棘爪收集者',
    'Thorny Saptor': '多刺的迅叶龙',
    'Thunderhead': '雷霆之颅',
    'Thundering Totem': '雷鸣图腾',
    'Tiny Felwyrm': '小小邪能浮龙',
    'Tormented Shade': '被折磨的影魔',
    'Torrent Totem': '洪流图腾',
    'Toxic Creeper': '剧毒蠕行者',
    'Trained Felhunter': '驯服的地狱猎犬',
    'Twinfang Harrower': '双牙蹂躏者',
    "Ula'tek's Chosen": '乌拉特克神选者',
    'Umbral Shadowbinder': '幽影缚影者',
    'Umbral Tentacle': '暗影触须',
    'Umbral War-Adept': '暗影战争精锐',
    'Umbral Warrior': '黯影战士',
    'Uncoiled Writhe': '溃散的扭缠蛇',
    'Underbrush Stalker': '灌林追猎者',
    'Unleashed Imp': '不羁的小鬼',
    'Unruly Textbook': '任性的教科书',
    'Unstable Phantom': '不稳定的幻影',
    'Unstable Voidling': '不稳定的虚空之子',
    'Venom Leech': '毒液水蛭',
    'Vexamus': '维克萨姆斯',
    'Viceroy Nezhar': '总督奈扎尔',
    'Vicious Ravager': '恶毒掠食者',
    'Vigilant Librarian': '警惕的图书管理员',
    'Vile Lasher': '恶毒的鞭笞者',
    'Virid Grovekeeper': '翠绿林地守护者',
    'Void Tentacle': '虚空触须',
    'Void Terror': '虚空恐魔',
    'Void-Infused Brightscale': '注虚亮鳞浮龙',
    'Void-Infused Destroyer': '注虚毁灭者',
    'Voidcaller': '虚空召唤者',
    'Voidling': '虚空之子',
    'Voidminder': '虚空看顾者',
    'VoidscarArena': '虚空之痕竞技场',
    'Voidtouched Magi': '虚触法师',
    'Volatile Totem': '动荡图腾',
    'Vordaza': '沃达扎',
    'Warding Mask': '结界面具',
    'Warehouse Worker': '仓库工人',
    'Watchful Harrower': '警惕的掠心者',
    'Wild Imp': '野生小鬼',
    'Windrunner Soldier': '风行士兵',
    'WindrunnerSpire': '风行者之塔',
    'Witherbark Prisoner': '枯木囚犯',
    'Wrathbone Enforcer': '怒骨执行者',
    'Wrathguard Flayer': '愤怒卫士掠夺者',
    'Ymirjar Graveblade': '伊米亚墓刃',
    "Zaib'yan": '扎伊比安',
    'Zanazal the Wise': '智者扎纳扎尔',
    'Zealous Reaver': '狂热的掠夺者',
    'Ziekett': '兹欧凯特',
    'Ziekket': '兹欧凯特',
    "Zul'jan": '祖尔加',
    "Zul'jarra": '祖尔加拉',
    'Zuraal the Ascended': '晋升者祖拉尔',
    '[DNT] Conduit Stalker': '[DNT] Conduit Stalker',

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
class ActorAbilityInfo:
    """某个首领 / 小怪在本场施放过的技能摘要（悬停血条用）。"""

    ability: str
    ability_id: int | None = None
    cast_count: int = 0
    ability_en: str | None = None
    icon: str | None = None
    description: str | None = None
    cast_label: str | None = None


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
