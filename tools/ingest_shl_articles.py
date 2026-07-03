#!/usr/bin/env python3
"""Ingest the 112 Shang Han Lun original articles (原文) into the database.

Usage:
    python tools/ingest_shl_articles.py --db       # Load into database
    python tools/ingest_shl_articles.py --json     # Export to JSON
    python tools/ingest_shl_articles.py --db --clear  # Clear and reload
"""

import argparse
import json
import os
import sys
import re

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
SRC_DIR = os.path.join(ROOT_DIR, 'src')
sys.path.insert(0, SRC_DIR)

# The 112 articles of the Shang Han Lun (Song version), organized by channel.
# Source: 宋本《伤寒论》— public domain classical Chinese medical text.
ARTICLES = [
    # ── 太阳病篇 (Tai Yang) — articles 1-30 ──
    (1, "tai_yang", "tai_yang_gang", "太阳之为病，脉浮，头项强痛而恶寒。", "Tai Yang disease: floating pulse, stiff neck and headache, aversion to cold."),
    (2, "tai_yang", "tai_yang_wind", "太阳病，发热，汗出，恶风，脉缓者，名为中风。", "Tai Yang disease with fever, sweating, aversion to wind, moderate pulse — called wind strike."),
    (3, "tai_yang", "tai_yang_cold", "太阳病，或已发热，或未发热，必恶寒，体痛，呕逆，脉阴阳俱紧者，名曰伤寒。", "Tai Yang disease with or without fever, aversion to cold, body aches, vomiting, tight pulse — called cold damage."),
    (4, "tai_yang", "transmission", "伤寒一日，太阳受之，脉若静者为不传；颇欲吐，若躁烦，脉数急者，为传也。", "On day one the Tai Yang receives it; if the pulse is calm, it hasn't transmitted."),
    (5, "tai_yang", "transmission", "伤寒二三日，阳明、少阳证不见者，为不传也。", "If after 2-3 days there are no Yangming or Shaoyang signs, it hasn't transmitted."),
    (6, "tai_yang", "wen_bing", "太阳病，发热而渴，不恶寒者，为温病。", "Tai Yang disease with fever, thirst, and no aversion to cold — warm disease."),
    (7, "tai_yang", "yin_yang", "病有发热恶寒者，发于阳也；无热恶寒者，发于阴也。", "Disease with fever and aversion to cold arises from yang; without fever arises from yin."),
    (8, "tai_yang", "healing", "太阳病，头痛至七日以上自愈者，以行其经尽故也。", "Tai Yang headache resolving after 7+ days means the channel cycle is complete."),
    (9, "tai_yang", "healing", "太阳病欲解时，从巳至未上。", "Tai Yang disease tends to resolve between 9am-3pm."),
    (10, "tai_yang", "healing", "风家，表解而不了了者，十二日愈。", "Wind-strike patients whose exterior resolves but feel unwell recover by day 12."),
    (11, "tai_yang", "yin_yang", "病人身大热，反欲得衣者，热在皮肤，寒在骨髓也；身大寒，反不欲近衣者，寒在皮肤，热在骨髓也。", "Fever with desire for clothing — heat in skin, cold in marrow. Cold with aversion to clothing — cold in skin, heat in marrow."),
    (12, "tai_yang", "gui_zhi_tang", "太阳中风，阳浮而阴弱，阳浮者热自发，阴弱者汗自出，啬啬恶寒，淅淅恶风，翕翕发热，鼻鸣干呕者，桂枝汤主之。", "Tai Yang wind strike: yang floating yin weak, spontaneous fever and sweating, aversion to wind, nasal congestion, dry heaves — Gui Zhi Tang governs."),
    (13, "tai_yang", "gui_zhi_tang", "太阳病，头痛，发热，汗出，恶风，桂枝汤主之。", "Tai Yang disease with headache, fever, sweating, aversion to wind — Gui Zhi Tang governs."),
    (14, "tai_yang", "gui_zhi_tang", "太阳病，项背强几几，反汗出恶风者，桂枝加葛根汤主之。", "Tai Yang disease with stiff neck and back, sweating, aversion to wind — Gui Zhi Jia Ge Gen Tang governs."),
    (15, "tai_yang", "gui_zhi_tang", "太阳病，下之后，其气上冲者，可与桂枝汤。", "Tai Yang disease treated with purging, if there is qi rushing upward — Gui Zhi Tang may be given."),
    (16, "tai_yang", "gui_zhi_tang", "太阳病三日，已发汗，若吐、若下、若温针，仍不解者，此为坏病，桂枝不中与之也。", "Tai Yang disease after 3 days with sweating, vomiting, purging, or warm needling still not resolved — it's a damaged case, Gui Zhi Tang is no longer suitable."),
    (17, "tai_yang", "contraindication", "若酒客病，不可与桂枝汤，得之则呕，以酒客不喜甘故也。", "For wine drinkers, do not give Gui Zhi Tang; it causes vomiting as they dislike sweetness."),
    (18, "tai_yang", "gui_zhi_tang", "喘家，作桂枝汤，加厚朴、杏子佳。", "For patients with asthma, add Hou Po and Xing Ren to Gui Zhi Tang."),
    (19, "tai_yang", "contraindication", "凡服桂枝汤吐者，其后必吐脓血也。", "Those who vomit after taking Gui Zhi Tang will later vomit pus and blood."),
    (20, "tai_yang", "gui_zhi_tang", "太阳病，发汗，遂漏不止，其人恶风，小便难，四肢微急，难以屈伸者，桂枝加附子汤主之。", "Tai Yang disease with sweating, continuous leakage, aversion to wind, difficult urination, limb tightness — Gui Zhi Jia Fu Zi Tang governs."),
    (21, "tai_yang", "gui_zhi_tang", "太阳病，下之后，脉促胸满者，桂枝去芍药汤主之。", "Tai Yang disease after purging: rapid pulse and chest fullness — Gui Zhi Qu Shao Yao Tang governs."),
    (22, "tai_yang", "gui_zhi_tang", "若微寒者，桂枝去芍药加附子汤主之。", "If there is also slight chills — Gui Zhi Qu Shao Yao Jia Fu Zi Tang governs."),
    (23, "tai_yang", "gui_zhi_ma_huang", "太阳病，得之八九日，如疟状，发热恶寒，热多寒少，其人不呕，清便欲自可，一日二三度发，脉微缓者，为欲愈也；脉微而恶寒者，此阴阳俱虚，不可更发汗、更下、更吐也；面色反有热色者，未欲解也，以其不能得小汗出，身必痒，宜桂枝麻黄各半汤。", "Tai Yang disease at 8-9 days: malaria-like fever/chills, more heat than cold, pulse slight and moderate — nearing recovery; pulse slight with chills — both yin and yang deficient, do not sweat/purge/vomit; flushed face — not yet resolved, body itching from lack of mild sweating — Gui Zhi Ma Huang Ge Ban Tang."),
    (24, "tai_yang", "gui_zhi_tang", "太阳病，初服桂枝汤，反烦不解者，先刺风池、风府，却与桂枝汤则愈。", "Tai Yang disease: after first dose of Gui Zhi Tang, if there is vexation without relief — first acupuncture at Fengchi and Fengfu, then give Gui Zhi Tang."),
    (25, "tai_yang", "gui_zhi_tang", "服桂枝汤，大汗出，脉洪大者，与桂枝汤如前法。若形似疟，一日再发者，汗出必解，宜桂枝二麻黄一汤。", "After Gui Zhi Tang with profuse sweating and surging pulse — give Gui Zhi Tang as before. If malaria-like with two episodes/day — Gui Zhi Er Ma Huang Yi Tang."),
    (26, "tai_yang", "bai_hu_tang", "服桂枝汤，大汗出后，大烦渴不解，脉洪大者，白虎加人参汤主之。", "After Gui Zhi Tang: profuse sweating, extreme thirst and vexation, surging pulse — Bai Hu Jia Ren Shen Tang governs."),
    (27, "tai_yang", "gui_zhi_tang", "太阳病，发热恶寒，热多寒少，脉微弱者，此无阳也，不可发汗，宜桂枝二越婢一汤。", "Tai Yang disease: fever and chills with more heat than cold, faint pulse — no yang, do not sweat — Gui Zhi Er Yue Bi Yi Tang."),
    (28, "tai_yang", "gui_zhi_tang", "服桂枝汤，或下之，仍头项强痛，翕翕发热，无汗，心下满微痛，小便不利者，桂枝去桂加茯苓白术汤主之。", "After Gui Zhi Tang or purging: stiff neck, fever, no sweat, epigastric fullness, difficult urination — Gui Zhi Qu Gui Jia Fu Ling Bai Zhu Tang governs."),
    (29, "tai_yang", "li_zhong_tang", "伤寒，脉浮，自汗出，小便数，心烦，微恶寒，脚挛急，反与桂枝欲攻其表，此误也。得之便厥，咽中干，烦躁吐逆者，作甘草干姜汤与之，以复其阳；若厥愈足温者，更作芍药甘草汤与之，其脚即伸；若胃气不和谵语者，少与调胃承气汤；若重发汗，复加烧针者，四逆汤主之。", "Cold damage: floating pulse, spontaneous sweating, frequent urination, vexation, chills, leg cramps — mistakenly given Gui Zhi Tang causes cold limbs, dry throat, irritability — give Gan Cao Gan Jiang Tang to restore yang; then Shao Yao Gan Cao Tang for leg extension; if delirium — Tiao Wei Cheng Qi Tang; if severe — Si Ni Tang."),
    (30, "tai_yang", "pattern", "问曰：证象阳旦，按法治之而增剧，厥逆，咽中干，两胫拘急而谵语。……", "Question: Pattern resembles Yangdan, but following the method worsens it..."),

    # ── 太阳病篇 (Tai Yang) — articles 31-60 ──
    (31, "tai_yang", "ge_gen_tang", "太阳病，项背强几几，无汗恶风，葛根汤主之。", "Tai Yang disease: stiff neck and back, no sweating, aversion to wind — Ge Gen Tang governs."),
    (32, "tai_yang", "ge_gen_tang", "太阳与阳明合病者，必自下利，葛根汤主之。", "Tai Yang and Yang Ming combined disease: spontaneous diarrhea — Ge Gen Tang governs."),
    (33, "tai_yang", "ge_gen_tang", "太阳与阳明合病，不下利，但呕者，葛根加半夏汤主之。", "Tai Yang and Yang Ming combined disease: no diarrhea but vomiting — Ge Gen Jia Ban Xia Tang governs."),
    (34, "tai_yang", "ge_gen_tang", "太阳病，桂枝证，医反下之，利遂不止，脉促者，表未解也；喘而汗出者，葛根黄芩黄连汤主之。", "Tai Yang disease with Gui Zhi pattern, mistakenly purged: continuous diarrhea, rapid pulse — exterior not resolved; panting with sweating — Ge Gen Huang Qin Huang Lian Tang governs."),
    (35, "tai_yang", "ma_huang_tang", "太阳病，头痛发热，身疼腰痛，骨节疼痛，恶风无汗而喘者，麻黄汤主之。", "Tai Yang disease: headache, fever, body aches, lower back pain, joint pain, aversion to wind, no sweating, panting — Ma Huang Tang governs."),
    (36, "tai_yang", "ma_huang_tang", "太阳与阳明合病，喘而胸满者，不可下，宜麻黄汤。", "Tai Yang and Yang Ming combined disease: panting and chest fullness — do not purge, use Ma Huang Tang."),
    (37, "tai_yang", "ma_huang_tang", "太阳病，十日以去，脉浮细而嗜卧者，外已解也；设胸满胁痛者，与小柴胡汤；脉但浮者，与麻黄汤。", "Tai Yang disease after 10 days: floating-fine pulse, drowsy — exterior resolved; chest and rib fullness — Xiao Chai Hu Tang; still floating pulse — Ma Huang Tang."),
    (38, "tai_yang", "da_qing_long_tang", "太阳中风，脉浮紧，发热恶寒，身疼痛，不汗出而烦躁者，大青龙汤主之。若脉微弱，汗出恶风者，不可服之；服之则厥逆，筋惕肉瞤，此为逆也。", "Tai Yang wind strike: floating-tight pulse, fever, chills, body aches, no sweating, irritability — Da Qing Long Tang governs. If pulse faint with sweating — do not give; it causes cold limbs and muscle twitching."),
    (39, "tai_yang", "da_qing_long_tang", "伤寒脉浮缓，身不疼，但重，乍有轻时，无少阴证者，大青龙汤发之。", "Cold damage: floating-moderate pulse, no pain but heaviness with periodic relief, no Shao Yin signs — Da Qing Long Tang to disperse."),
    (40, "tai_yang", "xiao_qing_long_tang", "伤寒，表不解，心下有水气，干呕发热而咳，或渴，或利，或噎，或小便不利，少腹满，或喘者，小青龙汤主之。", "Cold damage: exterior not resolved, water qi below the heart, dry heaves, fever, cough, with or without thirst, diarrhea, choking, difficult urination, lower abdominal fullness, panting — Xiao Qing Long Tang governs."),
    (41, "tai_yang", "xiao_qing_long_tang", "伤寒，心下有水气，咳而微喘，发热不渴；服汤已渴者，此寒去欲解也。小青龙汤主之。", "Cold damage: water qi below the heart, cough, mild panting, fever without thirst — Xiao Qing Long Tang governs. Thirst after taking means cold is leaving."),
    (42, "tai_yang", "gui_zhi_tang", "太阳病，外证未解，脉浮弱者，当以汗解，宜桂枝汤。", "Tai Yang disease: exterior pattern not resolved, floating-weak pulse — should sweat, use Gui Zhi Tang."),
    (43, "tai_yang", "gui_zhi_tang", "太阳病，下之微喘者，表未解故也，桂枝加厚朴杏子汤主之。", "Tai Yang disease after purging: mild panting — exterior not resolved — Gui Zhi Jia Hou Po Xing Zi Tang governs."),
    (44, "tai_yang", "gui_zhi_tang", "太阳病，外证未解，不可下也，下之为逆；欲解外者，宜桂枝汤。", "Tai Yang disease: exterior not resolved — do not purge; to resolve the exterior, use Gui Zhi Tang."),
    (45, "tai_yang", "gui_zhi_tang", "太阳病，先发汗不解，而复下之，脉浮者不愈。浮为在外，而反下之，故令不愈。今脉浮，故在外，当须解外则愈，宜桂枝汤。", "Tai Yang disease: sweat first then purge, still floating pulse — exterior not resolved, should use Gui Zhi Tang."),
    (46, "tai_yang", "ma_huang_tang", "太阳病，脉浮紧无汗，发热身疼痛，八九日不解，表证仍在，此当发其汗。服药已微除，其人发烦目瞑，剧者必衄，衄乃解。所以然者，阳气重故也。麻黄汤主之。", "Tai Yang disease: floating-tight pulse, no sweat, fever, body aches, 8-9 days unresolved — should sweat. After medicine: vexation, blurred vision, possible nosebleed — nosebleed resolves it. Ma Huang Tang governs."),
    (47, "tai_yang", "ma_huang_tang", "太阳病，脉浮紧，发热身无汗，自衄者愈。", "Tai Yang disease: floating-tight pulse, fever, no sweat — spontaneous nosebleed resolves it."),
    (48, "tai_yang", "pattern", "二阳并病，太阳初得病时发其汗，汗先出不彻，因转属阳明，续自微汗出，不恶寒。……", "Two yang combined disease: when Tai Yang first develops, sweat is applied incompletely, turning to Yang Ming..."),
    (49, "tai_yang", "contraindication", "脉浮数者，法当汗出而愈。若下之，身重心悸者，不可发汗，当自汗出乃解。", "Floating-rapid pulse: should sweat to cure. If purged causing heaviness and palpitations — do not sweat; let natural sweating resolve it."),
    (50, "tai_yang", "contraindication", "脉浮紧者，法当身疼痛，宜以汗解之。假令尺中迟者，不可发汗。何以知然？以荣气不足，血少故也。", "Floating-tight pulse: body aches, should sweat. If the cubit pulse is slow — do not sweat; nutritive qi is insufficient, blood is scarce."),
    (51, "tai_yang", "ma_huang_tang", "脉浮者，病在表，可发汗，宜麻黄汤。", "Floating pulse: disease in the exterior — can sweat, use Ma Huang Tang."),
    (52, "tai_yang", "ma_huang_tang", "脉浮而数者，可发汗，宜麻黄汤。", "Floating and rapid pulse — can sweat, use Ma Huang Tang."),
    (53, "tai_yang", "gui_zhi_tang", "病常自汗出，此为荣气和。荣气和者，外不谐，以卫气不共荣气和谐故尔。以荣行脉中，卫行脉外，复发其汗，荣卫和则愈，宜桂枝汤。", "Constant spontaneous sweating: nutritive qi is harmonious but defensive qi is not coordinated — sweat again to harmonize, use Gui Zhi Tang."),
    (54, "tai_yang", "gui_zhi_tang", "病人脏无他病，时发热自汗出而不愈者，此卫气不和也。先其时发汗则愈，宜桂枝汤。", "Patient with no organ disease: episodic fever and sweating — defensive qi is not harmonious. Sweat before the episode, use Gui Zhi Tang."),
    (55, "tai_yang", "ma_huang_tang", "伤寒脉浮紧，不发汗，因致衄者，麻黄汤主之。", "Cold damage: floating-tight pulse, no sweating, causing nosebleed — Ma Huang Tang governs."),
    (56, "tai_yang", "gui_zhi_tang", "伤寒，不大便六七日，头痛有热者，与承气汤；其小便清者，知不在里仍在表也，当须发汗。若头痛者必衄，宜桂枝汤。", "Cold damage: no bowel movement for 6-7 days, headache, fever — give Cheng Qi Tang; if urine is clear — not interior but exterior, should sweat, use Gui Zhi Tang."),
    (57, "tai_yang", "gui_zhi_tang", "伤寒发汗已解，半日许复烦，脉浮数者，可更发汗，宜桂枝汤。", "Cold damage: sweating resolves it, but after half a day vexation returns with floating-rapid pulse — can sweat again, use Gui Zhi Tang."),
    (58, "tai_yang", "healing", "凡病，若发汗，若吐，若下，若亡血，亡津液，阴阳自和者，必自愈。", "In any disease, after sweating, vomiting, purging, blood loss, or fluid loss — if yin and yang harmonize themselves, it will heal."),
    (59, "tai_yang", "healing", "大下之后，复发汗，小便不利者，亡津液故也。勿治之，得小便利，必自愈。", "After heavy purging then sweating: difficult urination — lost fluids. Don't treat it; when urination normalizes, it will heal."),
    (60, "tai_yang", "healing", "下之后，复发汗，必振寒，脉微细。所以然者，以内外俱虚故也。", "After purging then sweating: shivering chills, faint-thin pulse — both interior and exterior are deficient."),

    # ── 太阳病篇 (Tai Yang) — articles 61-90 ──
    (61, "tai_yang", "gan_jiang_tang", "下之后，复发汗，昼日烦躁不得眠，夜而安静，不呕不渴，无表证，脉沉微，身无大热者，干姜附子汤主之。", "After purging then sweating: daytime irritability with no sleep, calm at night, no vomiting/thirst, no exterior signs, deep-faint pulse — Gan Jiang Fu Zi Tang governs."),
    (62, "tai_yang", "gui_zhi_tang", "发汗后，身疼痛，脉沉迟者，桂枝加芍药生姜各一两人参三两新加汤主之。", "After sweating: body pains, deep-slow pulse — Gui Zhi Jia Shao Yao Sheng Jiang Ren Shen Xin Jia Tang governs."),
    (63, "tai_yang", "ma_huang_tang", "发汗后，不可更行桂枝汤。汗出而喘，无大热者，可与麻黄杏仁甘草石膏汤。", "After sweating: do not give Gui Zhi Tang again. Sweating with panting, no high fever — Ma Huang Xing Ren Gan Cao Shi Gao Tang."),
    (64, "tai_yang", "gui_zhi_tang", "发汗过多，其人叉手自冒心，心下悸，欲得按者，桂枝甘草汤主之。", "Excessive sweating: patient crosses hands over heart, palpitations, desire for pressure — Gui Zhi Gan Cao Tang governs."),
    (65, "tai_yang", "gui_zhi_tang", "发汗后，其人脐下悸者，欲作奔豚，茯苓桂枝甘草大枣汤主之。", "After sweating: palpitations below the navel, impending running piglet — Fu Ling Gui Zhi Gan Cao Da Zao Tang governs."),
    (66, "tai_yang", "gui_zhi_tang", "发汗后，腹胀满者，厚朴生姜半夏甘草人参汤主之。", "After sweating: abdominal fullness and distension — Hou Po Sheng Jiang Ban Xia Gan Cao Ren Shen Tang governs."),
    (67, "tai_yang", "gui_zhi_tang", "伤寒若吐若下后，心下逆满，气上冲胸，起则头眩，脉沉紧，发汗则动经，身为振振摇者，茯苓桂枝白术甘草汤主之。", "Cold damage after vomiting or purging: epigastric distension, qi rushing to chest, dizziness on standing, deep-tight pulse — Fu Ling Gui Zhi Bai Zhu Gan Cao Tang governs."),
    (68, "tai_yang", "gui_zhi_tang", "发汗病不解，反恶寒者，虚故也，芍药甘草附子汤主之。", "Sweating without resolution, instead worsening chills — deficiency — Shao Yao Gan Cao Fu Zi Tang governs."),
    (69, "tai_yang", "tiao_wei_cheng_qi", "发汗，若下之，病仍不解，烦躁者，茯苓四逆汤主之。", "After sweating or purging: disease not resolved, irritability — Fu Ling Si Ni Tang governs."),
    (70, "tai_yang", "tiao_wei_cheng_qi", "发汗后，恶寒者，虚故也；不恶寒，但热者，实也，当和胃气，与调胃承气汤。", "After sweating: chills indicate deficiency; no chills but fever indicates excess — harmonize the stomach — Tiao Wei Cheng Qi Tang."),
    (71, "tai_yang", "wu_ling_san", "太阳病，发汗后，大汗出，胃中干，烦躁不得眠，欲得饮水者，少少与饮之，令胃气和则愈。若脉浮，小便不利，微热消渴者，五苓散主之。", "Tai Yang disease after sweating: profuse sweating, dry stomach, irritability, thirst — give small amounts of water. If floating pulse, difficult urination, mild fever, consuming thirst — Wu Ling San governs."),
    (72, "tai_yang", "wu_ling_san", "发汗已，脉浮数，烦渴者，五苓散主之。", "After sweating: floating-rapid pulse, vexation and thirst — Wu Ling San governs."),
    (73, "tai_yang", "wu_ling_san", "伤寒，汗出而渴者，五苓散主之；不渴者，茯苓甘草汤主之。", "Cold damage: sweating with thirst — Wu Ling San governs; without thirst — Fu Ling Gan Cao Tang governs."),
    (74, "tai_yang", "wu_ling_san", "中风发热，六七日不解而烦，有表里证，渴欲饮水，水入则吐者，名曰水逆，五苓散主之。", "Wind strike with fever, 6-7 days unresolved, vexation, both exterior and interior signs, thirst with vomiting after drinking — water reversal — Wu Ling San governs."),
    (75, "tai_yang", "pattern", "未持脉时，病人手叉自冒心，师因教试令咳而不咳者，此必两耳聋无闻也。所以然者，以重发汗，虚故如此。", "Before taking the pulse, patient crosses hands over heart; asked to cough but can't — deafness from excessive sweating and deficiency."),
    (76, "tai_yang", "zhi_zi_tang", "发汗后，水药不得入口，为逆；若更发汗，必吐下不止。发汗吐下后，虚烦不得眠，若剧者，必反复颠倒，心中懊憹，栀子豉汤主之。", "After sweating: cannot take water or medicine — adverse. If sweat again, vomiting and diarrhea won't stop. After sweating/vomiting/purging: deficient vexation, insomnia, severe restlessness, chest anguish — Zhi Zi Chi Tang governs."),
    (77, "tai_yang", "zhi_zi_tang", "发汗若下之，而烦热胸中窒者，栀子豉汤主之。", "After sweating or purging: vexation, heat, chest stuffiness — Zhi Zi Chi Tang governs."),
    (78, "tai_yang", "zhi_zi_tang", "伤寒五六日，大下之后，身热不去，心中结痛者，未欲解也，栀子豉汤主之。", "Cold damage 5-6 days after heavy purging: persistent fever, knotted pain in the heart — not yet resolved — Zhi Zi Chi Tang governs."),
    (79, "tai_yang", "zhi_zi_tang", "伤寒下后，心烦腹满，卧起不安者，栀子厚朴汤主之。", "Cold damage after purging: vexation, abdominal fullness, restlessness — Zhi Zi Hou Po Tang governs."),
    (80, "tai_yang", "zhi_zi_tang", "伤寒，医以丸药大下之，身热不去，微烦者，栀子干姜汤主之。", "Cold damage: doctor used pill medicine for heavy purging, persistent fever, mild vexation — Zhi Zi Gan Jiang Tang governs."),
    (81, "tai_yang", "contraindication", "凡用栀子汤，病人旧微溏者，不可与服之。", "When using Zhi Zi Tang: if patient has chronic loose stools, do not give it."),
    (82, "tai_yang", "zhen_wu_tang", "太阳病发汗，汗出不解，其人仍发热，心下悸，头眩，身瞤动，振振欲擗地者，真武汤主之。", "Tai Yang disease after sweating: unresolved fever, palpitations, dizziness, muscle twitching, shaky and about to fall — Zhen Wu Tang governs."),
    (83, "tai_yang", "contraindication", "咽喉干燥者，不可发汗。", "Dry throat — do not sweat."),
    (84, "tai_yang", "contraindication", "淋家，不可发汗，汗出必便血。", "Strangury patient — do not sweat; sweating causes blood in urine."),
    (85, "tai_yang", "contraindication", "疮家，虽身疼痛，不可发汗，汗出则痉。", "Sores patient — even with body pain, do not sweat; sweating causes convulsions."),
    (86, "tai_yang", "contraindication", "衄家，不可发汗，汗出必须上陷，脉急紧，直视不能眴，不得眠。", "Nosebleed patient — do not sweat; sweating causes sunken supraorbital, tight pulse, staring eyes, insomnia."),
    (87, "tai_yang", "contraindication", "亡血家，不可发汗，发汗则寒栗而振。", "Blood-loss patient — do not sweat; sweating causes chills and shivering."),
    (88, "tai_yang", "contraindication", "汗家重发汗，必恍惚心乱，小便已阴疼，与禹余粮丸。", "Sweat-prone patient re-sweated: confusion, painful urination — Yu Yu Liang Wan."),
    (89, "tai_yang", "contraindication", "病人有寒，复发汗，胃中冷，必吐蛔。", "Patient with cold: re-sweating causes cold stomach and roundworm vomiting."),
    (90, "tai_yang", "pattern", "本发汗而复下之，此为逆也；若先发汗，治不为逆。本先下之而反汗之，为逆；若先下之，治不为逆。", "Should sweat but purged instead — adverse. Should purge but sweated instead — adverse."),

    # ── 太阳病篇 (Tai Yang) — articles 91-127 ──
    (91, "tai_yang", "pattern", "伤寒，医下之，续得下利清谷不止，身疼痛者，急当救里；后身疼痛，清便自调者，急当救表。救里宜四逆汤，救表宜桂枝汤。", "Cold damage: doctor purged, continuous diarrhea with undigested food, body pain — urgently treat interior. After stools normalize — urgently treat exterior. Interior: Si Ni Tang. Exterior: Gui Zhi Tang."),
    (92, "tai_yang", "pattern", "病发热头痛，脉反沉，若不差，身体疼痛，当救其里，四逆汤方。", "Disease with fever, headache, but deep pulse — if not improving, body pain — treat interior, Si Ni Tang."),
    (93, "tai_yang", "pattern", "太阳病，先下而不愈，因复发汗，以此表里俱虚，其人因致冒，冒家汗出自愈。所以然者，汗出表和故也。里未和，然后复下之。", "Tai Yang disease: purged first without cure, then sweated — both exterior and interior deficient, causing dizziness. Sweating resolves it when exterior is harmonized. If interior not harmonized, then purge."),
    (94, "tai_yang", "pattern", "太阳病未解，脉阴阳俱停，必先振栗汗出而解。但阳脉微者，先汗出而解；但阴脉微者，下之而解。若欲下之，宜调胃承气汤。", "Tai Yang disease unresolved, both pulses submerged — first shivering then sweating resolves it. If only yang pulse is faint — sweating resolves. If only yin pulse is faint — purging resolves."),
    (95, "tai_yang", "gui_zhi_tang", "太阳病，发热汗出者，此为荣弱卫强，故使汗出，欲救邪风者，宜桂枝汤。", "Tai Yang disease: fever and sweating — weak nutritive, strong defensive — to rescue from pathogenic wind, use Gui Zhi Tang."),
    (96, "tai_yang", "xiao_chai_hu_tang", "伤寒五六日中风，往来寒热，胸胁苦满，嘿嘿不欲饮食，心烦喜呕，或胸中烦而不呕，或渴，或腹中痛，或胁下痞硬，或心下悸小便不利，或不渴身有微热，或咳者，小柴胡汤主之。", "Cold damage or wind strike at 5-6 days: alternating fever and chills, chest and rib fullness, silent, no appetite, vexation, vomiting — Xiao Chai Hu Tang governs."),
    (97, "tai_yang", "xiao_chai_hu_tang", "血弱气尽，腠理开，邪气因入，与正气相搏，结于胁下。正邪分争，往来寒热，休作有时，嘿嘿不欲饮食。脏腑相连，其痛必下，邪高痛下，故使呕也，小柴胡汤主之。", "Blood weak, qi exhausted, interstices open, pathogen enters, struggles with right qi, knots below the ribs. Right and pathogen contend — alternating fever and chills. Xiao Chai Hu Tang governs."),
    (98, "tai_yang", "contraindication", "得病六七日，脉迟浮弱，恶风寒，手足温，医二三下之，不能食而胁下满痛，面目及身黄，颈项强，小便难者，与柴胡汤，后必下重。", "Disease at 6-7 days: slow-floating-weak pulse, chills, warm limbs — purged 2-3 times — no appetite, rib fullness and pain, jaundice, stiff neck, difficult urination — if given Chai Hu Tang, will have tenesmus."),
    (99, "tai_yang", "xiao_chai_hu_tang", "伤寒四五日，身热恶风，颈项强，胁下满，手足温而渴者，小柴胡汤主之。", "Cold damage 4-5 days: fever, aversion to wind, stiff neck, rib fullness, warm limbs, thirst — Xiao Chai Hu Tang governs."),
    (100, "tai_yang", "xiao_chai_hu_tang", "伤寒，阳脉涩，阴脉弦，法当腹中急痛，先与小建中汤；不差者，小柴胡汤主之。", "Cold damage: rough yang pulse, tight yin pulse — acute abdominal pain — first Xiao Jian Zhong Tang; if not better — Xiao Chai Hu Tang."),
    (101, "tai_yang", "xiao_chai_hu_tang", "伤寒中风，有柴胡证，但见一证便是，不必悉具。凡柴胡汤病证而下之，若柴胡证不罢者，复与柴胡汤，必蒸蒸而振，却复发热汗出而解。", "Cold damage or wind strike with Chai Hu pattern: seeing one sign is enough, need not all be present. If Chai Hu pattern persists after purging — give Chai Hu Tang again, steaming shivering, then fever and sweating resolves it."),
    (102, "tai_yang", "xiao_jian_zhong", "伤寒二三日，心中悸而烦者，小建中汤主之。", "Cold damage 2-3 days: palpitations and vexation — Xiao Jian Zhong Tang governs."),
    (103, "tai_yang", "da_chai_hu_tang", "太阳病，过经十余日，反二三下之，后四五日，柴胡证仍在者，先与小柴胡汤。呕不止，心下急，郁郁微烦者，为未解也，与大柴胡汤下之则愈。", "Tai Yang disease after 10+ days, purged 2-3 times, after 4-5 days Chai Hu pattern still present — give Xiao Chai Hu Tang. If vomiting unceasing, epigastric tightness, depression and vexation — Da Chai Hu Tang."),
    (104, "tai_yang", "chai_hu_tang", "伤寒十三日不解，胸胁满而呕，日晡所发潮热，已而微利。此本柴胡证，下之以不得利，今反利者，知医以丸药下之，此非其治也。潮热者，实也。先宜服小柴胡汤以解外，后以柴胡加芒硝汤主之。", "Cold damage 13 days unresolved: chest and rib fullness, vomiting, tidal fever, mild diarrhea — originally Chai Hu pattern, doctor used pill purgative — wrong treatment. Xiao Chai Hu Tang first, then Chai Hu Jia Mang Xiao Tang."),
    (105, "tai_yang", "pattern", "伤寒十三日，过经谵语者，以有热也，当以汤下之。……", "Cold damage 13 days: channel passage delirium — there is heat, should use decoction to purge."),
    (106, "tai_yang", "tao_he_cheng_qi", "太阳病不解，热结膀胱，其人如狂，血自下，下者愈。其外不解者，尚未可攻，当先解其外；外解已，但少腹急结者，乃可攻之，宜桃核承气汤。", "Tai Yang disease unresolved: heat binds in the bladder, manic behavior, spontaneous blood discharge — resolves. If exterior not resolved — treat exterior first. If only lower abdominal tightness — attack with Tao He Cheng Qi Tang."),
    (107, "tai_yang", "chai_hu_tang", "伤寒八九日，下之，胸满烦惊，小便不利，谵语，一身尽重，不可转侧者，柴胡加龙骨牡蛎汤主之。", "Cold damage 8-9 days after purging: chest fullness, vexation, fright, difficult urination, delirium, heavy body unable to turn — Chai Hu Jia Long Gu Mu Li Tang governs."),
    (108, "tai_yang", "pattern", "伤寒，腹满谵语，寸口脉浮而紧，此肝乘脾也，名曰纵，刺期门。", "Cold damage: abdominal fullness, delirium, floating-tight寸口 pulse — liver overacting on spleen — acupuncture at LR14."),
    (109, "tai_yang", "pattern", "伤寒发热，啬啬恶寒，大渴欲饮水，其腹必满，自汗出，小便利，其病欲解，此肝乘肺也，名曰横，刺期门。", "Cold damage: fever, aversion to cold, great thirst with abdominal fullness, spontaneous sweating, normal urination — liver overacting on lung — acupuncture at LR14."),
    (110, "tai_yang", "pattern", "太阳病二日，反躁，凡熨其背而大汗出……", "Tai Yang disease at 2 days: irritability, hot compresses on back causing profuse sweating..."),
    (111, "tai_yang", "pattern", "太阳病中风，以火劫发汗。邪风被火热，血气流溢，失其常度……", "Tai Yang wind strike: fire-forcing sweat. Wind pathogen meets fire heat, blood and qi overflow, losing their normal regulation..."),
    (112, "tai_yang", "pattern", "伤寒脉浮，医以火迫劫之，亡阳必惊狂，卧起不安者，桂枝去芍药加蜀漆牡蛎龙骨救逆汤主之。", "Cold damage: floating pulse, doctor fire-forced sweat — yang loss causing mania, terrified, restless — Gui Zhi Qu Shao Yao Jia Shu Qi Mu Li Long Gu Jiu Ni Tang governs."),
    (113, "tai_yang", "pattern", "形作伤寒，其脉不弦紧而弱。弱者必渴，被火必谵语……", "Appears like cold damage but pulse not tight — weak pulse means thirst; fire treatment causes delirium..."),
    (114, "tai_yang", "pattern", "太阳病，以火熏之，不得汗，其人必躁；到经不解，必清血，名为火邪。", "Tai Yang disease: fire-fumigation without sweating — patient becomes irritable; if not resolved by channel cycle — blood in stool, called fire pathogen."),
    (115, "tai_yang", "pattern", "脉浮热甚，而反灸之，此为实。实以虚治，因火而动，必咽燥吐血。", "Floating pulse with severe fever: moxibustion applied instead — excess treated as deficiency — fire moves, causing dry throat and blood-spitting."),
    (116, "tai_yang", "pattern", "微数之脉，慎不可灸。因火为邪，则为烦逆，追虚逐实，血散脉中……", "Faint-rapid pulse: do not moxa. Fire as pathogen causes vexation and rebellion, pursues deficiency and chases excess, blood scatters in the vessels..."),
    (117, "tai_yang", "pattern", "烧针令其汗，针处被寒，核起而赤者，必发奔豚。气从少腹上冲心者，灸其核上各一壮，与桂枝加桂汤。", "Warm needling to cause sweat: needle site invaded by cold, red lump — running piglet develops. Qi rushes from lower abdomen to heart — moxa the lump one cone each, give Gui Zhi Jia Gui Tang."),
    (118, "tai_yang", "gui_zhi_tang", "火逆下之，因烧针烦躁者，桂枝甘草龙骨牡蛎汤主之。", "Fire-rebellion treated by purging, then warm needling causing irritability — Gui Zhi Gan Cao Long Gu Mu Li Tang governs."),
    (119, "tai_yang", "contraindication", "太阳伤寒者，加温针必惊也。", "Tai Yang cold damage: adding warm needling causes fright."),
    (120, "tai_yang", "pattern", "太阳病，当恶寒发热，今自汗出，反不恶寒发热，关上脉细数者，以医吐之过也。", "Tai Yang disease: should have chills and fever but has spontaneous sweating without chills/fever, thin-rapid guan pulse — doctor's error in vomiting."),
    (121, "tai_yang", "pattern", "太阳病吐之，但太阳病当恶寒，今反不恶寒，不欲近衣，此为吐之内烦也。", "Tai Yang disease: vomited — should have chills but doesn't, doesn't want clothing — internal vexation from vomiting."),
    (122, "tai_yang", "pattern", "病人脉数，数为热，当消谷引食，而反吐者，此以发汗，令阳气微，膈气虚，脉乃数也。数为客热，不能消谷，以胃中虚冷，故吐也。", "Rapid pulse: should indicate heat with good appetite, but instead vomiting — sweating caused yang qi depletion, diaphragm qi deficiency. The rapid pulse is guest heat, not digesting food — stomach deficient cold causes vomiting."),
    (123, "tai_yang", "pattern", "太阳病，过经十余日，心下温温欲吐而胸中痛，大便反溏，腹微满，郁郁微烦，先此时自极吐下者，与调胃承气汤。", "Tai Yang disease after 10+ days: nausea, chest pain, loose stool, mild abdominal fullness, depression — if patient had severe vomiting/purging before — Tiao Wei Cheng Qi Tang."),
    (124, "tai_yang", "di_dang_tang", "太阳病六七日，表证仍在，脉微而沉，反不结胸，其人发狂者，以热在下焦，少腹当硬满，小便自利者，下血乃愈。所以然者，以太阳随经，瘀热在里故也，抵当汤主之。", "Tai Yang disease 6-7 days: exterior signs remain, faint-deep pulse, no chest binding, mania — heat in lower jiao, hard lower abdomen, normal urination — blood discharge cures it. Di Dang Tang governs."),
    (125, "tai_yang", "di_dang_tang", "太阳病身黄，脉沉结，少腹硬，小便不利者，为无血也；小便自利，其人如狂者，血证谛也，抵当汤主之。", "Tai Yang disease with jaundice, deep-knotted pulse, hard lower abdomen — if difficult urination: no blood stasis; if normal urination with manic behavior: blood sign confirmed — Di Dang Tang governs."),
    (126, "tai_yang", "di_dang_tang", "伤寒有热，少腹满，应小便不利，今反利者，为有血也，当下之，不可余药，宜抵当丸。", "Cold damage with heat, full lower abdomen — should have difficult urination but instead normal — blood stasis, should attack — Di Dang Wan."),
    (127, "tai_yang", "pattern", "太阳病，小便利者，以饮水多，必心下悸；小便少者，必苦里急也。", "Tai Yang disease: normal urination with excessive drinking — palpitations below heart; scant urination — lower abdominal urgency."),

    # ── 阳明病篇 (Yang Ming) — articles 128-178 ──
    (128, "yang_ming", "yang_ming_gang", "问曰：病有太阳阳明，有正阳阳明，有少阳阳明，何谓也？答曰：太阳阳明者，脾约是也；正阳阳明者，胃家实是也；少阳阳明者，发汗利小便已，胃中燥烦实，大便难是也。", "Yang Ming has three types: Tai Yang Yang Ming (spleen constraint), Zheng Yang Yang Ming (stomach excess), Shao Yang Yang Ming (sweating/urination causes dry stomach, difficult bowels)."),
    (129, "yang_ming", "pattern", "阳明之为病，胃家实是也。", "Yang Ming disease: stomach and intestines excess."),
    (130, "yang_ming", "pattern", "问曰：何缘得阳明病？答曰：太阳病，若发汗若下若利小便，此亡津液，胃中干燥，因转属阳明。不更衣，内实，大便难者，此名阳明也。", "How does Yang Ming disease arise? Tai Yang disease with sweating, purging, or diuresis — fluid loss, dry stomach, turning to Yang Ming. Constipation, internal excess, difficult bowels — this is Yang Ming."),
    (131, "yang_ming", "pattern", "问曰：阳明病外证云何？答曰：身热，汗自出，不恶寒，反恶热也。", "What are the external signs of Yang Ming disease? Fever, spontaneous sweating, no chills, aversion to heat."),
    (132, "yang_ming", "pattern", "问曰：病有得之一日，不发热而恶寒者，何也？答曰：虽得之一日，恶寒将自罢，即自汗出而恶热也。", "On the first day of Yang Ming: no fever but chills — chills will stop, then spontaneous sweating and aversion to heat."),
    (133, "yang_ming", "pattern", "问曰：恶寒何故自罢？答曰：阳明居中，主土也，万物所归，无所复传。始虽恶寒，二日自止，此为阳明病也。", "Why do chills stop? Yang Ming is central, governs earth, all things return to it — no further transmission. Chills stop on day 2 — this is Yang Ming disease."),
    (134, "yang_ming", "yang_ming_pattern", "本太阳病，初得病时发其汗，汗先出不彻，因转属阳明也。", "Originally Tai Yang disease with sweating that was insufficient — turns to Yang Ming."),
    (135, "yang_ming", "yang_ming_pattern", "伤寒发热无汗，呕不能食，而反汗出濈濈然者，是转属阳明也。", "Cold damage: fever no sweat, vomiting unable to eat, then continuous sweating — turning to Yang Ming."),
    (136, "yang_ming", "cheng_qi_tang", "阳明病，脉迟，虽汗出不恶寒者，其身必重，短气腹满而喘，有潮热者，此外欲解，可攻里也。手足濈然汗出者，此大便已硬也，大承气汤主之。", "Yang Ming: slow pulse, sweating without chills, heavy body, short breath, abdominal fullness, tidal fever — exterior about to resolve, can attack interior. Sweating hands and feet — hard stool — Da Cheng Qi Tang governs."),
    (137, "yang_ming", "cheng_qi_tang", "阳明病，潮热，大便微硬者，可与大承气汤；不硬者，不可与之。", "Yang Ming: tidal fever, slightly hard stool — Da Cheng Qi Tang. Not hard — do not give."),
    (138, "yang_ming", "cheng_qi_tang", "阳明病，不吐不下，心烦者，可与调胃承气汤。", "Yang Ming: without vomiting or purging, vexation — Tiao Wei Cheng Qi Tang."),
    (139, "yang_ming", "cheng_qi_tang", "阳明病，脉迟，汗出多，微恶寒者，表未解也，可发汗，宜桂枝汤。", "Yang Ming: slow pulse, profuse sweating, mild chills — exterior not resolved — Gui Zhi Tang."),
    (140, "yang_ming", "cheng_qi_tang", "阳明病，脉浮，无汗而喘者，发汗则愈，宜麻黄汤。", "Yang Ming: floating pulse, no sweat, panting — sweat cures it — Ma Huang Tang."),
    (141, "yang_ming", "pattern", "阳明病，但头眩，不恶寒，故能食而咳，其人咽必痛；若不咳者，咽不痛。", "Yang Ming: dizziness, no chills, able to eat, cough — throat pain. Without cough — no throat pain."),
    (142, "yang_ming", "pattern", "阳明病，无汗，小便不利，心中懊憹者，身必发黄。", "Yang Ming: no sweat, difficult urination, chest anguish — jaundice develops."),
    (143, "yang_ming", "pattern", "阳明病，被火，额上微汗出，而小便不利者，身必发黄。", "Yang Ming treated with fire: slight forehead sweating, difficult urination — jaundice develops."),
    (144, "yang_ming", "cheng_qi_tang", "阳明病，脉浮而紧者，必潮热，发作有时；但浮者，必盗汗出。", "Yang Ming: floating-tight pulse — tidal fever at regular times. Only floating — night sweating."),
    (145, "yang_ming", "pattern", "阳明病，口燥但欲漱水不欲咽者，此必衄。", "Yang Ming: dry mouth, wants to rinse but not swallow — nosebleed."),
    (146, "yang_ming", "pattern", "阳明病，本自汗出，医更重发汗，病已差，尚微烦不了了者，此必大便硬故也。以亡津液，胃中干燥，故令大便硬。当问其小便日几行，若本小便日三四行，今日再行者，故知大便不久出。今为小便数少，以津液当还入胃中，故知不久必大便也。", "Yang Ming: originally sweating, doctor re-sweated — disease resolved but mild vexation — dry stool from lost fluids. Ask about urination — if decreased, fluids return to stomach, stool will pass."),
    (147, "yang_ming", "pattern", "伤寒呕多，虽有阳明证，不可攻之。", "Cold damage with much vomiting — even with Yang Ming signs, do not attack."),
    (148, "yang_ming", "pattern", "阳明病，心下硬满者，不可攻之。攻之，利遂不止者死；利止者愈。", "Yang Ming: epigastric hardness and fullness — do not attack. If attacked causing continuous diarrhea — fatal; if diarrhea stops — recovers."),
    (149, "yang_ming", "pattern", "阳明病，面合色赤，不可攻之。必发热，色黄者，小便不利也。", "Yang Ming: red facial complexion — do not attack. Fever and yellow discoloration with difficult urination."),
    (150, "yang_ming", "pattern", "阳明病，不吐不下，心烦者，可与调胃承气汤。", "Yang Ming: without vomiting or purging, vexation — Tiao Wei Cheng Qi Tang."),
    (151, "yang_ming", "pattern", "阳明病，发潮热，大便溏，小便自可，胸胁满不去者，与小柴胡汤。", "Yang Ming: tidal fever, loose stool, normal urination, persistent chest and rib fullness — Xiao Chai Hu Tang."),
    (152, "yang_ming", "pattern", "阳明病，胁下硬满，不大便而呕，舌上白苔者，可与小柴胡汤。上焦得通，津液得下，胃气因和，身濈然汗出而解。", "Yang Ming: hard fullness below ribs, no bowel movement, vomiting, white tongue coating — Xiao Chai Hu Tang. Upper jiao opens, fluids descend, stomach qi harmonizes, sweating resolves it."),
    (153, "yang_ming", "pattern", "阳明中风，脉弦浮大而短气，腹都满，胁下及心痛，久按之气不通，鼻干，不得汗，嗜卧，一身及目悉黄，小便难，有潮热，时时哕，耳前后肿，刺之小差。外不解，病过十日，脉续浮者，与小柴胡汤。", "Yang Ming wind strike: string-like-floating-large pulse, short breath, full abdomen, rib and heart pain, nasal dryness, no sweat, drowsy, jaundice, difficult urination, tidal fever, hiccups, ear swelling — acupuncture helps. After 10 days with floating pulse — Xiao Chai Hu Tang."),
    (154, "yang_ming", "pattern", "阳明病，脉迟，汗出多，微恶寒者，表未解也，可发汗，宜桂枝汤。", "Yang Ming: slow pulse, profuse sweating, mild chills — exterior not resolved — Gui Zhi Tang."),
    (155, "yang_ming", "pattern", "阳明病，脉浮，无汗而喘者，发汗则愈，宜麻黄汤。", "Yang Ming: floating pulse, no sweat, panting — sweat cures — Ma Huang Tang."),
    (156, "yang_ming", "huang_lian_tang", "阳明病，发热汗出者，此为热越，不能发黄也；但头汗出，身无汗，剂颈而还，小便不利，渴引水浆者，此为瘀热在里，身必发黄，茵陈蒿汤主之。", "Yang Ming: fever, sweating everywhere — heat escapes, no jaundice. If only head sweats, no body sweat, difficult urination, thirst — stagnant heat in interior, jaundice — Yin Chen Hao Tang governs."),
    (157, "yang_ming", "pattern", "阳明证，其人喜忘者，必有蓄血。所以然者，本有久瘀血，故令喜忘。屎虽硬，大便反易，其色必黑者，宜抵当汤下之。", "Yang Ming pattern with forgetfulness — blood stagnation. Stool hard but passes easily, black color — Di Dang Tang."),
    (158, "yang_ming", "pattern", "阳明病，下之，心中懊憹而烦，胃中有燥屎者，可攻。腹微满，初头硬，后必溏，不可攻之。若有燥屎者，宜大承气汤。", "Yang Ming after purging: chest anguish, vexation — dry stool in stomach — attack. Mild fullness with initial hardness then loose — do not attack."),
    (159, "yang_ming", "pattern", "病人不大便五六日，绕脐痛，烦躁，发作有时者，此有燥屎，故使不大便也。", "Patient no bowel movement 5-6 days, pain around umbilicus, periodic irritability — dry stool."),
    (160, "yang_ming", "pattern", "病人烦热，汗出则解，又如疟状，日晡所发热者，属阳明也。脉实者，宜下之；脉浮虚者，宜发汗。", "Vexing heat relieved by sweating, then malaria-like, tidal fever at dusk — Yang Ming. Excess pulse — purge. Floating-empty pulse — sweat."),
    (161, "yang_ming", "pattern", "大下后，六七日不大便，烦不解，腹满痛者，此有燥屎也。所以然者，本有宿食故也，宜大承气汤。", "After heavy purging, 6-7 days no bowel movement, unrelieved vexation, abdominal pain — dry stool from retained food — Da Cheng Qi Tang."),
    (162, "yang_ming", "pattern", "病人小便不利，大便乍难乍易，时有微热，喘冒不能卧者，有燥屎也，宜大承气汤。", "Difficult urination, alternating bowel habits, mild fever, panting, dizziness, unable to lie down — dry stool — Da Cheng Qi Tang."),
    (163, "yang_ming", "pattern", "食谷欲呕，属阳明也，吴茱萸汤主之。得汤反剧者，属上焦也。", "Vomiting after eating — Yang Ming — Wu Zhu Yu Tang governs. If worse after taking — upper jiao pattern."),
    (164, "yang_ming", "pattern", "太阳病，寸缓关浮尺弱，其人发热汗出，复恶寒，不呕，但心下痞者，此以医下之也。", "Tai Yang disease with slow-tight pulse, fever, sweating, chills, no vomiting, but epigastric stuffness — doctor purged."),
    (165, "yang_ming", "pattern", "伤寒，发热，汗出不解，心中痞硬，呕吐而下利者，大柴胡汤主之。", "Cold damage: fever unrelieved by sweating, stuffness and hardness below heart, vomiting, diarrhea — Da Chai Hu Tang governs."),
    (166, "yang_ming", "pattern", "阳明病，发潮热，大便溏，小便自可，胸胁满不去者，与柴胡汤。", "Yang Ming: tidal fever, loose stool, normal urine, persistent chest/rib fullness — Chai Hu Tang."),
    (167, "yang_ming", "pattern", "病胁下素有痞，连在脐旁，痛引少腹入阴筋者，此名藏结，死。", "Chronic mass below ribs connecting to umbilicus, pain radiating to lower abdomen and genitals — organ binding — fatal."),
    (168, "yang_ming", "bai_hu_tang", "伤寒若吐若下后，七八日不解，热结在里，表里俱热，时时恶风，大渴，舌上干燥而烦，欲饮水数升者，白虎加人参汤主之。", "Cold damage after vomiting/purging, 7-8 days unresolved, heat bound in interior, both exterior and interior hot, periodic chills, great thirst, dry tongue — Bai Hu Jia Ren Shen Tang governs."),
    (169, "yang_ming", "bai_hu_tang", "伤寒，无大热，口燥渴，心烦，背微恶寒者，白虎加人参汤主之。", "Cold damage: no high fever, dry mouth, thirst, vexation, mild back chills — Bai Hu Jia Ren Shen Tang governs."),
    (170, "yang_ming", "bai_hu_tang", "伤寒，脉浮，发热无汗，其表不解，不可与白虎汤。渴欲饮水，无表证者，白虎加人参汤主之。", "Cold damage: floating pulse, fever, no sweat — exterior not resolved — do not give Bai Hu Tang. Thirst without exterior signs — Bai Hu Jia Ren Shen Tang."),
    (171, "yang_ming", "pattern", "太阳少阳并病，心下硬，颈项强而眩者，当刺大椎、肺俞、肝俞，慎勿下之。", "Tai Yang and Shao Yang combined: epigastric hardness, stiff neck, dizziness — acupuncture at DU14, BL13, BL18 — do not purge."),
    (172, "yang_ming", "pattern", "太阳与少阳合病，自下利者，与黄芩汤；若呕者，黄芩加半夏生姜汤主之。", "Tai Yang and Shao Yang combined: spontaneous diarrhea — Huang Qin Tang; with vomiting — Huang Qin Jia Ban Xia Sheng Jiang Tang."),
    (173, "yang_ming", "pattern", "伤寒，胸中有热，胃中有邪气，腹中痛，欲呕吐者，黄连汤主之。", "Cold damage: heat in chest, pathogenic qi in stomach, abdominal pain, nausea — Huang Lian Tang governs."),
    (174, "yang_ming", "pattern", "伤寒八九日，风湿相搏，身体疼烦，不能自转侧，不呕不渴，脉浮虚而涩者，桂枝附子汤主之；若其人大便硬，小便自利者，去桂加白术汤主之。", "Cold damage 8-9 days: wind-damp contention, painful body, unable to turn, no vomiting/thirst, floating-empty-rough pulse — Gui Zhi Fu Zi Tang. If hard stool, normal urination — Qu Gui Jia Bai Zhu Tang."),
    (175, "yang_ming", "pattern", "风湿相搏，骨节疼烦，掣痛不得屈伸，近之则痛剧，汗出短气，小便不利，恶风不欲去衣，或身微肿者，甘草附子汤主之。", "Wind-damp contention: painful joints, pulling pain unable to flex, worsened by touch, sweating, short breath, difficult urination, aversion to wind, mild edema — Gan Cao Fu Zi Tang governs."),
    (176, "yang_ming", "bai_hu_tang", "伤寒，脉浮滑，此以表有热，里有寒，白虎汤主之。", "Cold damage: floating-smooth pulse — heat in exterior, cold in interior — Bai Hu Tang governs."),
    (177, "yang_ming", "pattern", "伤寒脉结代，心动悸，炙甘草汤主之。", "Cold damage: knotted-skipping pulse, palpitations — Zhi Gan Cao Tang governs."),
    (178, "yang_ming", "pattern", "脉按之来缓，时一止复来者，名曰结；又脉来动而中止，更来小数，中有还者反动，名曰结阴也；脉来动而中止，不能自还，因而复动者，名曰代阴也。得此脉者，必难治。", "Slow pulse with occasional pause — knotted. Moving pulse that stops and resumes — knotted yin. Moving pulse that stops and cannot return — skipped yin. Difficult to treat."),

    # ── 少阳病篇 (Shao Yang) — articles 179-186 ──
    (179, "shao_yang", "shao_yang_gang", "少阳之为病，口苦，咽干，目眩也。", "Shao Yang disease: bitter taste, dry throat, dizziness."),
    (180, "shao_yang", "pattern", "少阳中风，两耳无所闻，目赤，胸中满而烦者，不可吐下，吐下则悸而惊。", "Shao Yang wind strike: deafness, red eyes, chest fullness, vexation — do not vomit or purge; vomiting/purging causes palpitations and fright."),
    (181, "shao_yang", "pattern", "伤寒，脉弦细，头痛发热者，属少阳。少阳不可发汗，发汗则谵语。", "Cold damage: string-thin pulse, headache, fever — Shao Yang. Do not sweat; sweating causes delirium."),
    (182, "shao_yang", "pattern", "本太阳病不解，转入少阳者，胁下硬满，干呕不能食，往来寒热，尚未吐下，脉沉紧者，与小柴胡汤。", "Tai Yang disease unresolved, turning to Shao Yang: hard fullness below ribs, dry heaves, no appetite, alternating chills/fever — Xiao Chai Hu Tang."),
    (183, "shao_yang", "pattern", "若已吐下发汗温针，谵语，柴胡汤证罢，此为坏病。知犯何逆，以法治之。", "If already vomited, purged, sweated, warm needled — delirium, Chai Hu pattern gone — damaged case. Treat according to the error."),
    (184, "shao_yang", "pattern", "伤寒三日，少阳脉小者，欲已也。", "Cold damage day 3: Shao Yang pulse small — about to resolve."),
    (185, "shao_yang", "pattern", "少阳病欲解时，从寅至辰上。", "Shao Yang disease tends to resolve between 3-7am."),

    # ── 太阴病篇 (Tai Yin) — articles 186-196 ──
    (186, "tai_yin", "tai_yin_gang", "太阴之为病，腹满而吐，食不下，自利益甚，时腹自痛。若下之，必胸下结硬。", "Tai Yin disease: abdominal fullness, vomiting, no appetite, worsening diarrhea, periodic abdominal pain. If purged — hardness below the chest."),
    (187, "tai_yin", "pattern", "太阴中风，四肢烦疼，阳微阴涩而长者，为欲愈。", "Tai Yin wind strike: painful limbs, faint yang pulse, rough yin pulse becoming long — about to heal."),
    (188, "tai_yin", "pattern", "太阴病欲解时，从亥至丑上。", "Tai Yin disease tends to resolve between 9pm-1am."),
    (189, "tai_yin", "pattern", "太阴病，脉浮者，可发汗，宜桂枝汤。", "Tai Yin disease with floating pulse — can sweat, use Gui Zhi Tang."),
    (190, "tai_yin", "pattern", "自利不渴者，属太阴，以其脏有寒故也，当温之，宜服四逆辈。", "Diarrhea without thirst — Tai Yin, visceral cold — warm it, use Si Ni category."),
    (191, "tai_yin", "pattern", "伤寒脉浮而缓，手足自温者，系在太阴。太阴当发身黄；若小便自利者，不能发黄。至七八日，虽暴烦下利日十余行，必自止，以脾家实，腐秽当去故也。", "Cold damage: floating-moderate pulse, warm limbs — Tai Yin. Should develop jaundice; if urination normal — no jaundice. At 7-8 days sudden vexation with 10+ diarrhea episodes — stops naturally — spleen excess, rot eliminated."),
    (192, "tai_yin", "pattern", "本太阳病，医反下之，因尔腹满时痛者，属太阴也，桂枝加芍药汤主之；大实痛者，桂枝加大黄汤主之。", "Originally Tai Yang, doctor purged instead — abdominal fullness and pain — Tai Yin. Gui Zhi Jia Shao Yao Tang. Severe pain — Gui Zhi Jia Da Huang Tang."),
    (193, "tai_yin", "pattern", "太阴为病，脉弱，其人续自便利，设当行大黄芍药者，宜减之，以其人胃气弱，易动故也。", "Tai Yin disease: weak pulse, continuous diarrhea — if needing Da Huang or Shao Yao, reduce dosage — stomach qi is weak, easily moved."),

    # ── 少阴病篇 (Shao Yin) — articles 197-218 ──
    (194, "shao_yin", "shao_yin_gang", "少阴之为病，脉微细，但欲寐也。", "Shao Yin disease: faint-thin pulse, only desire to sleep."),
    (195, "shao_yin", "pattern", "少阴病，欲吐不吐，心烦，但欲寐，五六日自利而渴者，属少阴也，虚故引水自救。若小便色白者，少阴病形悉具。小便白者，以下焦虚有寒，不能制水，故令色白也。", "Shao Yin: nausea without vomiting, vexation, drowsy, after 5-6 days diarrhea with thirst — deficiency drawing water for self-help. White urine — all Shao Yin signs present. Lower jiao deficient cold, unable to control water."),
    (196, "shao_yin", "pattern", "病人脉阴阳俱紧，反汗出者，亡阳也。此属少阴，法当咽痛而复吐利。", "Both yin and yang pulses tight with sweating — yang loss. Shao Yin — sore throat, vomiting, diarrhea."),
    (197, "shao_yin", "pattern", "少阴病，咳而下利，谵语者，被火气劫故也，小便必难，以强责少阴汗也。", "Shao Yin: cough, diarrhea, delirium — fire-forced sweating — difficult urination from forcing Shao Yin sweat."),
    (198, "shao_yin", "pattern", "少阴病，脉细沉数，病为在里，不可发汗。", "Shao Yin: thin-deep-rapid pulse — disease in the interior, do not sweat."),
    (199, "shao_yin", "pattern", "少阴病，脉微，不可发汗，亡阳故也。阳已虚，尺脉弱涩者，复不可下之。", "Shao Yin: faint pulse — do not sweat, yang loss. Yang deficient with weak-rough cubit pulse — also do not purge."),
    (200, "shao_yin", "pattern", "少阴病，脉紧，至七八日，自下利，脉暴微，手足反温，脉紧反去者，为欲解也，虽烦下利，必自愈。", "Shao Yin: tight pulse, at 7-8 days spontaneous diarrhea, pulse suddenly faint, limbs warm instead of cold — about to resolve. Despite vexation and diarrhea, will self-heal."),
    (201, "shao_yin", "si_ni_tang", "少阴病，下利清谷，里寒外热，手足厥逆，脉微欲绝，身反不恶寒，其人面色赤，或腹痛，或干呕，或咽痛，或利止脉不出者，通脉四逆汤主之。", "Shao Yin: diarrhea with undigested food, interior cold exterior heat, cold limbs, barely perceptible pulse, no chills, red face, with or without pain, dry heaves, sore throat, pulse non-detectable — Tong Mai Si Ni Tang governs."),
    (202, "shao_yin", "si_ni_tang", "少阴病，饮食入口则吐，心中温温欲吐复不能吐。始得之，手足寒，脉弦迟者，此胸中实，不可下也，当吐之。若膈上有寒饮，干呕者，不可吐也，当温之，宜四逆汤。", "Shao Yin: vomiting upon eating, nausea without vomiting, cold hands and feet, string-slow pulse — chest excess, do not purge, vomit it. If cold rheum above diaphragm with dry heaves — do not vomit, warm with Si Ni Tang."),
    (203, "shao_yin", "zhen_wu_tang", "少阴病，二三日不已，至四五日，腹痛，小便不利，四肢沉重疼痛，自下利者，此为有水气。其人或咳，或小便利，或下利，或呕者，真武汤主之。", "Shao Yin unrelieved at 2-3 days, by 4-5 days: abdominal pain, difficult urination, heavy painful limbs, diarrhea — water qi. With cough, or normal urine, or diarrhea, or vomiting — Zhen Wu Tang governs."),
    (204, "shao_yin", "pattern", "少阴病，下利清谷，里寒外热，手足厥逆，脉微欲绝，身反不恶寒，其人面色赤，或腹痛，或干呕，或咽痛，或利止脉不出者，通脉四逆汤主之。", "Shao Yin: diarrhea with undigested food, interior cold, exterior heat, cold limbs, faint pulse, no chills, red face — Tong Mai Si Ni Tang."),
    (205, "shao_yin", "pattern", "少阴病，四逆，其人或咳，或悸，或小便不利，或腹中痛，或泄利下重者，四逆散主之。", "Shao Yin: cold limbs, with or without cough, palpitations, difficult urination, abdominal pain, tenesmus — Si Ni San governs."),
    (206, "shao_yin", "pattern", "少阴病，下利六七日，咳而呕渴，心烦不得眠者，猪苓汤主之。", "Shao Yin: diarrhea 6-7 days, cough, vomiting, thirst, vexation, insomnia — Zhu Ling Tang governs."),
    (207, "shao_yin", "pattern", "少阴病，得之二三日，口燥咽干者，急下之，宜大承气汤。", "Shao Yin at 2-3 days: dry mouth and throat — urgently purge — Da Cheng Qi Tang."),
    (208, "shao_yin", "pattern", "少阴病，自利清水，色纯青，心下必痛，口干燥者，可下之，宜大承气汤。", "Shao Yin: diarrhea of clear green water, epigastric pain, dry mouth — can purge — Da Cheng Qi Tang."),
    (209, "shao_yin", "pattern", "少阴病，六七日，腹胀不大便者，急下之，宜大承气汤。", "Shao Yin 6-7 days: abdominal distension, no bowel movement — urgently purge — Da Cheng Qi Tang."),
    (210, "shao_yin", "pattern", "少阴病，脉沉者，急温之，宜四逆汤。", "Shao Yin: deep pulse — urgently warm — Si Ni Tang."),
    (211, "shao_yin", "pattern", "少阴病，饮食入口则吐，心中温温欲吐复不能吐……宜四逆汤。", "Shao Yin: vomiting upon eating — Si Ni Tang."),
    (212, "shao_yin", "pattern", "少阴病，下利，脉微涩，呕而汗出，必数更衣，反少者，当温其上，灸之。", "Shao Yin: diarrhea, faint-rough pulse, vomiting, sweating, frequent small bowel movements — warm the upper, moxibustion."),

    # ── 厥阴病篇 (Jue Yin) — articles 213-222 ──
    (213, "jue_yin", "jue_yin_gang", "厥阴之为病，消渴，气上撞心，心中疼热，饥而不欲食，食则吐蛔，下之利不止。", "Jue Yin disease: wasting thirst, qi rushing to heart, heart pain and heat, hungry but no appetite, vomiting roundworms after eating, purging causes unceasing diarrhea."),
    (214, "jue_yin", "pattern", "厥阴中风，脉微浮为欲愈，不浮为未愈。", "Jue Yin wind strike: faint-floating pulse — about to heal. Not floating — not yet healed."),
    (215, "jue_yin", "pattern", "厥阴病欲解时，从丑至卯上。", "Jue Yin disease tends to resolve between 1-5am."),
    (216, "jue_yin", "pattern", "厥阴病，渴欲饮水者，少少与之愈。", "Jue Yin: thirst with desire to drink — give small amounts, it will heal."),
    (217, "jue_yin", "pattern", "诸四逆厥者，不可下之，虚家亦然。", "All cold reversal conditions — do not purge. Same for deficient patients."),
    (218, "jue_yin", "pattern", "伤寒，脉微而厥，至七八日肤冷，其人躁无暂安时者，此为藏厥，非蚘厥也。蚘厥者，其人当吐蚘。今病者静，而复时烦者，此为藏寒。蚘上入其膈，故烦，须臾复止，得食而呕又烦者，蚘闻食臭出，其人常自吐蚘。蚘厥者，乌梅丸主之。又主久利。", "Cold damage: faint pulse, cold limbs, at 7-8 days skin cold, unceasing agitation — visceral reversal, not roundworm reversal. Roundworm reversal: patient vomits roundworms, periodic vexation from worms entering the diaphragm, triggered by eating — Wu Mei Wan governs. Also treats chronic diarrhea."),
    (219, "jue_yin", "pattern", "伤寒，热少微厥，指头寒，嘿嘿不欲食，烦躁，数日小便利，色白者，此热除也。欲得食，其病为愈。若厥而呕，胸胁烦满者，其后必便血。", "Cold damage: mild heat, slight cold limbs, cool fingertips, silent, no appetite, irritability — after days if urine clear — heat removed. If cold limbs with vomiting, chest and rib fullness — later blood in stool."),
    (220, "jue_yin", "pattern", "病者手足厥冷，言我不结胸，小腹满，按之痛者，此冷结在膀胱关元也。", "Patient with cold hands and feet: says no chest binding, lower abdominal fullness, pain on pressure — cold binding in bladder and CV4."),
    (221, "jue_yin", "pattern", "伤寒发热四日，厥反三日，复热四日，厥少热多者，其病当愈。四日至七日热不除者，必便脓血。", "Cold damage: fever 4 days, cold reversal 3 days, then fever 4 days — less cold than heat — should heal. If fever persists from day 4-7 — blood and pus in stool."),
    (222, "jue_yin", "pattern", "伤寒，厥四日，热反三日，复厥五日，其病为进。寒多热少，阳气退，故为进也。", "Cold damage: cold reversal 4 days, fever 3 days, then cold 5 days — disease advancing. More cold than heat — yang qi retreating."),

    # ── 霍乱病篇 (Huo Luan) — articles 223-231 ──
    (223, "huo_luan", "pattern", "问曰：病有霍乱者何？答曰：呕吐而利，此名霍乱。", "Question: what is Huo Luan? Answer: vomiting and diarrhea — this is called Huo Luan."),
    (224, "huo_luan", "pattern", "问曰：病发热头痛，身疼恶寒，吐利者，此属何病？答曰：此名霍乱。霍乱自吐下，又利止，复更发热也。", "Fever, headache, body aches, chills, vomiting, diarrhea — Huo Luan. Huo Luan has spontaneous vomiting and diarrhea; when diarrhea stops, fever returns."),
    (225, "huo_luan", "pattern", "伤寒，其脉微涩者，本是霍乱，今是伤寒，却四五日至阴经上，转入阴必利。本呕下利者，不可治也。欲似大便而反失气，仍不利者，此属阳明也，便必硬，十三日愈。", "Faint-rough pulse — originally Huo Luan, now cold damage. Entering yin channels at 4-5 days — diarrhea. Originally vomiting and diarrhea — treatable."),
    (226, "huo_luan", "pattern", "恶寒脉微而复利，利止亡血也，四逆加人参汤主之。", "Chills, faint pulse, diarrhea — when diarrhea stops, blood has been lost — Si Ni Jia Ren Shen Tang governs."),
    (227, "huo_luan", "pattern", "霍乱，头痛发热身疼痛，热多欲饮水者，五苓散主之；寒多不用水者，理中丸主之。", "Huo Luan: headache, fever, body aches — more heat with thirst — Wu Ling San. More cold without thirst — Li Zhong Wan."),
    (228, "huo_luan", "pattern", "吐利止而身痛不休者，当消息和解其外，宜桂枝汤小和之。", "When vomiting and diarrhea stop but body pain persists — harmonize the exterior — Gui Zhi Tang."),

    # ── 阴阳易差后劳复病篇 ──
    (229, "post_recovery", "pattern", "大病差后，劳复者，枳实栀子豉汤主之。", "After recovery from major illness, overexertion causes relapse — Zhi Shi Zhi Zi Chi Tang governs."),
    (230, "post_recovery", "pattern", "伤寒差以后，更发热，小柴胡汤主之。脉浮者，以汗解之；脉沉实者，以下解之。", "After cold damage recovery: recurring fever — Xiao Chai Hu Tang. Floating pulse — sweat. Deep-excess pulse — purge."),
    (231, "post_recovery", "pattern", "大病差后，从腰以下有水气者，牡蛎泽泻散主之。", "After recovery: water qi below the waist — Mu Li Ze Xie San governs."),
    (232, "post_recovery", "pattern", "大病差后，喜唾，久不了了，胸上有寒，当以丸药温之，宜理中丸。", "After recovery: persistent salivation, long unrelieved — cold above the chest — warm with pill medicine — Li Zhong Wan."),
    (233, "post_recovery", "pattern", "伤寒解后，虚羸少气，气逆欲吐，竹叶石膏汤主之。", "After cold damage resolution: deficient, emaciated, short of breath, nausea — Zhu Ye Shi Gao Tang governs."),
    (234, "post_recovery", "pattern", "病人脉已解，而日暮微烦，以病新差，人强与谷，脾胃气尚弱，不能消谷，故令微烦，损谷则愈。", "Patient's pulse resolved but mild evening vexation — just recovered, forced to eat, spleen-stomach qi still weak, can't digest — reduce food and it heals."),
]


def main():
    parser = argparse.ArgumentParser(description="Ingest SHL articles")
    parser.add_argument('--db', action='store_true', help='Load into database')
    parser.add_argument('--json', action='store_true', help='Export to JSON')
    parser.add_argument('--clear', action='store_true', help='Clear existing articles first')
    parser.add_argument('--all', action='store_true', help='Do both --db and --json')
    args = parser.parse_args()

    if args.all:
        args.db = args.json = True
    if not any([args.db, args.json]):
        args.all = True
        args.db = args.json = True

    if args.db:
        import database as dblib
        dblib.init_db()
        if args.clear:
            dblib.clear_articles()
            print("Articles table cleared")

    entries = []
    for num, channel, pattern, zh, en in ARTICLES:
        entry = {"article_num": num, "channel": channel, "pattern": pattern, "original_zh": zh, "translation_en": en}
        entries.append(entry)

        if args.db:
            import database as dblib
            dblib.save_article(num, channel, pattern, zh, en)

        sys.stdout.write(f"\r  Article {num:3d} / {len(ARTICLES)} ({channel})")
        sys.stdout.flush()

    print()

    if args.db:
        import database as dblib
        print(f"DB:  {dblib.article_count()} articles in {dblib.DB_PATH}")

    if args.json:
        outpath = os.path.join(SRC_DIR, 'data', 'shl_articles.json')
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"JSON: {outpath}  ({len(entries)} articles)")

    print("Done.")


if __name__ == '__main__':
    main()
