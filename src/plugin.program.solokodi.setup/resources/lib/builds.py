import xbmcgui

from . import build_config


def _card_list_item(card):
    """Build a rich ListItem (icon + tagline) for the build selector."""
    if card["requires_debrid"]:
        hint = "Real-Debrid recommended"
    else:
        hint = "No subscriptions required"
    label2 = card.get("tagline") or hint
    item = xbmcgui.ListItem(label="{0}  -  v{1}".format(card["name"], card["version"]))
    item.setLabel2(label2)
    image = card.get("card_image")
    if image:
        item.setArt({"icon": image, "thumb": image, "poster": image})
    plot = card.get("description") or ""
    if card.get("tagline"):
        plot = "{0}\n\n{1}".format(card["tagline"], plot)
    item.setInfo("video", {"title": card["name"], "plot": plot})
    return item


def choose_build(preselect_id=None):
    """Show the rich build chooser. Returns a profile id, or None if cancelled."""
    cards = build_config.build_cards()
    if not cards:
        return None

    items = [_card_list_item(card) for card in cards]
    preselect = 0
    for index, card in enumerate(cards):
        if card["id"] == preselect_id:
            preselect = index
            break

    choice = xbmcgui.Dialog().select(
        "Choose your SoLoKodi build",
        items,
        useDetails=True,
        preselect=preselect,
    )
    if choice < 0:
        return None
    return cards[choice]["id"]


def show_build_picker():
    """Pick a build then launch its setup wizard. Returns True if a build was set."""
    from . import wizard

    current = build_config.profile_id() or None
    chosen = choose_build(preselect_id=current)
    if not chosen:
        return False

    build_config.set_active_profile(chosen)
    wizard.run_setup_wizard()
    return True
