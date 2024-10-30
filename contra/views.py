"""Views."""

import copy
from datetime import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import F
from django.shortcuts import render
from django.utils import timezone
from esi.errors import TokenError
from esi.models import Token

from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.hooks import get_extension_logger

from . import providers

logger = get_extension_logger(__name__)


def validate_char_token(char_id: int):
    scopes = [
        "esi-wallet.read_corporation_wallets.v1",
        "esi-characters.read_corporation_roles.v1",
        "esi-corporations.read_divisions.v1",
    ]

    req_roles = ["CEO", "Director"]

    tokens = Token.objects.filter(character_id=char_id).require_scopes(scopes)

    for token in tokens:
        try:
            if req_roles:
                roles = (
                    providers.esi.client.Character.get_characters_character_id_roles(
                        character_id=token.character_id,
                        token=token.valid_access_token(),
                    ).result()
                )

                has_roles = False

                # do we have the roles.
                for role in roles.get("roles", []):
                    if role in req_roles:
                        has_roles = True
                        break

                if has_roles:
                    return token  # return the token
                else:
                    pass  # next! TODO should we flag this character?
            else:
                return token  # no roles check needed return the token
        except TokenError as e:
            #  I've had invalid tokens in auth that refresh but don't actually work
            logger.error(f"Token Error ID: {token.pk} ({e})")

    return None


def get_corp_wallet_divisions(corp_id, token):
    divisions = (
        providers.esi.client.Corporation.get_corporations_corporation_id_divisions(
            corporation_id=corp_id, token=token.valid_access_token()
        ).result()
    )

    divisions = divisions.get("wallet")

    for division in divisions:
        division["division"] = str(division["division"])
        if division["division"] == "1":
            division["name"] = "Master Wallet"

    return divisions


def is_current_month(date):
    now = datetime.now()
    return date.year == now.year and date.month == now.month


def get_corp_wallet_division_journal(corp_id, token, wallet_division):
    current_page = 1
    total_pages = 1
    _new_names = []
    while current_page <= total_pages:
        journal_items = providers.esi.client.Wallet.get_corporations_corporation_id_wallets_division_journal(
            corporation_id=corp_id,
            division=wallet_division,
            page=current_page,
            token=token.valid_access_token(),
        )
        journal_items.request_config.also_return_response = True
        journal_items, headers = journal_items.result()
        total_pages = int(headers.headers["X-Pages"])
        logger.debug(
            f"CT: Corp {corp_id} Div {wallet_division}, Page:{current_page}/{total_pages} ({len(journal_items)})"
        )
        _min_time = timezone.now()
        items = []
        for item in journal_items:
            if _min_time > item.get("date"):
                _min_time = item.get("date")

            if is_current_month(item.get("date")):
                items.append(item)

        logger.info(
            f"CT: Corp {corp_id} Div {wallet_division}, Page: {current_page}, New Transactions! {len(items)}, New Names {_new_names}"
        )

        current_page += 1

    logger.info(f"CT: Corp {corp_id} Div {wallet_division}, OLDEST DATA! {_min_time}")

    return items


def get_corp_main_chars_dic(corp_id):
    main_chars = EveCharacter.objects.filter(
        character_ownership__isnull=False,
        character_ownership__user__profile__main_character__character_id=F(
            "character_id"
        ),
        corporation_id=corp_id,
    ).values("character_id", "character_name")

    main_chars = {
        char["character_id"]: {
            "character_id": char["character_id"],
            "character_name": char["character_name"],
            "paid": False,
            "donated_amount": 0.0,
        }
        for char in main_chars
    }

    return main_chars


def build_player_donation_dictionary(journal, char_dic, corp_id, target_amount=0):
    for item in journal:
        isPlayerDonation = item.get("ref_type") == "player_donation"
        isMainCharDonation = item.get("first_party_id") in char_dic
        isCorpDonation = item.get("second_party_id") == corp_id

        if isPlayerDonation and isMainCharDonation and isCorpDonation:
            char = char_dic[item["first_party_id"]]

            char["donated_amount"] += item.get("amount")

            if char["donated_amount"] >= target_amount:
                char["paid"] = True

    return char_dic


@login_required
@permission_required("contra.basic_access")
def index(request):
    selected_wallet_id = request.GET.get("wallet_id")
    target_amount_str = request.GET.get("target_amount", "0")

    try:
        target_amount = float(target_amount_str.replace(",", ""))
    except ValueError:
        target_amount = 0.0

    mainChar = request.user.profile.main_character
    corp_id = mainChar.corporation_id

    corpMainCharsDic = get_corp_main_chars_dic(corp_id)

    token = validate_char_token(char_id=mainChar.character_id)

    walletDivisions = get_corp_wallet_divisions(corp_id, token)

    context = {
        "walletDivisions": walletDivisions,
        "selected_wallet_id": selected_wallet_id,
        "target_amount": target_amount,
    }

    if selected_wallet_id:
        walletJournal = get_corp_wallet_division_journal(
            corp_id, token, selected_wallet_id
        )

        walletJournal = build_player_donation_dictionary(
            copy.deepcopy(walletJournal), corpMainCharsDic, corp_id, target_amount
        )

        walletJournal = sorted(
            list(walletJournal.values()),
            key=lambda x: (not x["paid"], x["character_name"].lower()),
        )

        context["characters"] = walletJournal

    """Render index view."""
    return render(request, "contra/index.html", context)
