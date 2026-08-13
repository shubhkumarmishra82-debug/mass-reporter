# ------------------------------------------------
# Created by: Dileep
# Copyright © 2026
# ------------------------------------------------
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# Report category tree based on Telegram's actual report reasons
REPORT_TREE = {
    "i_dont_like_it": {
        "label": "ðŸ™… I Don't Like It",
        "reason": "spam",
        "message": "I don't like this content",
        "subcategories": {}
    },
    "child_abuse": {
        "label": "ðŸ§’ Child Abuse",
        "reason": "childAbuse",
        "message": "Child abuse",
        "subcategories": {
            "child_sexual": {
                "label": "ðŸ”ž Child Sexual Abuse",
                "reason": "childAbuse",
                "message": "Child sexual abuse content",
                "subcategories": {}
            },
            "child_physical": {
                "label": "ðŸ’¥ Child Physical Abuse",
                "reason": "childAbuse",
                "message": "Child physical abuse content",
                "subcategories": {}
            }
        }
    },
    "violence": {
        "label": "âš”ï¸ Violence",
        "reason": "violence",
        "message": "Violent content",
        "subcategories": {
            "insults_false_info": {
                "label": "ðŸ—£ Insults & False Information",
                "reason": "violence",
                "message": "Insults and false information",
                "subcategories": {}
            },
            "graphic_disturbing": {
                "label": "ðŸ©¸ Graphic & Disturbing Content",
                "reason": "violence",
                "message": "Graphic and disturbing content",
                "subcategories": {}
            },
            "extreme_violence": {
                "label": "â˜ ï¸ Extreme Violence / Dismemberment",
                "reason": "violence",
                "message": "Extreme violence and dismemberment",
                "subcategories": {}
            },
            "hate_speech": {
                "label": "ðŸš« Hate Speech & Symbols",
                "reason": "violence",
                "message": "Hate speech and symbols",
                "subcategories": {}
            },
            "calling_violence": {
                "label": "ðŸ“¢ Calling for Violence",
                "reason": "violence",
                "message": "Calling for violence",
                "subcategories": {}
            },
            "organized_crime": {
                "label": " ðŸ”« Organized Crime",
                "reason": "violence",
                "message": "Organized crime",
                "subcategories": {}
            },
            "terrorism": {
                "label": "ðŸ’£ Terrorism",
                "reason": "violence",
                "message": "Terrorism related content",
                "subcategories": {}
            },
            "animal_abuse": {
                "label": "ðŸ¾ Animal Abuse",
                "reason": "violence",
                "message": "Animal abuse",
                "subcategories": {}
            }
        }
    },
    "illegal_goods": {
        "label": "ðŸ’¼ Illegal Goods & Services",
        "reason": "illegalDrugs",
        "message": "Illegal goods and services",
        "subcategories": {
            "weapons": {
                "label": "ðŸ”« Weapons",
                "reason": "illegalDrugs",
                "message": "Illegal weapons trade",
                "subcategories": {
                    "firearms": {
                        "label": "ðŸ”« Firearms",
                        "reason": "illegalDrugs",
                        "message": "Illegal firearms",
                        "subcategories": {}
                    },
                    "explosives": {
                        "label": "ðŸ’£ Explosives",
                        "reason": "illegalDrugs",
                        "message": "Illegal explosives",
                        "subcategories": {}
                    },
                    "ammo": {
                        "label": "ðŸŽ¯ Ammunition",
                        "reason": "illegalDrugs",
                        "message": "Illegal ammunition",
                        "subcategories": {}
                    }
                }
            },
            "drugs": {
                "label": "ðŸ’Š Drugs",
                "reason": "illegalDrugs",
                "message": "Illegal drugs",
                "subcategories": {
                    "narcotics": {
                        "label": "ðŸ’Š Narcotics",
                        "reason": "illegalDrugs",
                        "message": "Illegal narcotics",
                        "subcategories": {}
                    },
                    "prescription": {
                        "label": "ðŸ’‰ Prescription Drugs",
                        "reason": "illegalDrugs",
                        "message": "Illegal prescription drugs",
                        "subcategories": {}
                    },
                    "synthetic": {
                        "label": "ðŸ§ª Synthetic Drugs",
                        "reason": "illegalDrugs",
                        "message": "Synthetic drugs",
                        "subcategories": {}
                    },
                    "opioids": {
                        "label": "ðŸ’‰ Opioids",
                        "reason": "illegalDrugs",
                        "message": "Illegal opioids",
                        "subcategories": {}
                    }
                }
            },
            "counterfeit": {
                "label": "ðŸ’° Counterfeit Money",
                "reason": "illegalDrugs",
                "message": "Counterfeit currency",
                "subcategories": {}
            },
            "fraud": {
                "label": "ðŸŽ­ Fraud & Scams",
                "reason": "illegalDrugs",
                "message": "Fraud and scams",
                "subcategories": {}
            },
            "human_trafficking": {
                "label": "ðŸš¨ Human Trafficking",
                "reason": "illegalDrugs",
                "message": "Human trafficking",
                "subcategories": {}
            }
        }
    },
    "spam": {
        "label": "ðŸ“¨ Spam",
        "reason": "spam",
        "message": "Spam content",
        "subcategories": {}
    },
    "pornography": {
        "label": "ðŸ”ž Pornography",
        "reason": "pornography",
        "message": "Pornographic content",
        "subcategories": {}
    },
    "copyright": {
        "label": "Â©ï¸ Copyright Violation",
        "reason": "copyright",
        "message": "Copyright violation",
        "subcategories": {}
    },
    "personal_data": {
        "label": "ðŸ“‹ Personal Data Leak",
        "reason": "personalData",
        "message": "Personal data leak",
        "subcategories": {}
    },
    "fake_account": {
        "label": "ðŸŽ­ Fake Account",
        "reason": "fake",
        "message": "Fake account",
        "subcategories": {}
    }
}


def get_top_level_buttons() -> InlineKeyboardMarkup:
    """Get the top-level report category buttons."""
    buttons = []
    row = []
    keys = list(REPORT_TREE.keys())
    for i, key in enumerate(keys):
        cat = REPORT_TREE[key]
        has_subs = bool(cat.get("subcategories"))
        cb_data = f"rpt_sub_{key}" if has_subs else f"rpt_final_{key}"
        row.append(InlineKeyboardButton(cat["label"], callback_data=cb_data))
        if len(row) == 2 or i == len(keys) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_target")])
    return InlineKeyboardMarkup(buttons)


def get_subcategory_buttons(category_key: str) -> InlineKeyboardMarkup:
    """Get subcategory buttons for a given category."""
    category = REPORT_TREE
    for part in category_key.split("."):
        if part in category:
            cat = category[part]
            category = cat.get("subcategories", {})
        else:
            break
    
    if not category:
        return get_top_level_buttons()
    
    buttons = []
    row = []
    keys = list(category.keys())
    for i, key in enumerate(keys):
        cat = category[key]
        full_key = f"{category_key}.{key}"
        has_subs = bool(cat.get("subcategories"))
        cb_data = f"rpt_sub_{full_key}" if has_subs else f"rpt_final_{full_key}"
        row.append(InlineKeyboardButton(cat["label"], callback_data=cb_data))
        if len(row) == 2 or i == len(keys) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="rpt_back")])
    return InlineKeyboardMarkup(buttons)


def get_report_reason(category_key: str) -> tuple:
    """Get the report reason and message for a final category selection.
    Returns (reason, message) tuple."""
    parts = category_key.split(".")
    category = REPORT_TREE
    result = None
    
    for part in parts:
        if part in category:
            result = category[part]
            category = result.get("subcategories", {})
        else:
            break
    
    if result:
        return result.get("reason", "spam"), result.get("message", "Report")
    return "spam", "Report"
