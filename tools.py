from datetime import datetime, timezone


def _ok(action: str, detail: str) -> dict:
    return {
        "status": "success",
        "action": action,
        "detail": detail,
        "simulated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def reset_vpn_profile(username: str) -> dict:
    return _ok(
        "reset_vpn_profile",
        f"Ran \\\\IT-TOOLS\\Scripts\\reset-vpn-profile.ps1 for {username}. "
        "SCEP certificate regenerated (~90 s). Gateway confirmed as vpn-gp.limmatica.corp.",
    )


def restart_print_spooler(floor: str = "unknown") -> dict:
    return _ok(
        "restart_print_spooler",
        f"Print Spooler restarted on PRINT01.limmatica.corp (reported floor: {floor}). "
        "Queue cleared. PaperCut sync verified.",
    )


def clear_credential_manager(username: str) -> dict:
    return _ok(
        "clear_credential_manager",
        f"Removed MicrosoftOffice16_Data:* entries from Windows Credential Manager for {username}. "
        "Outlook will prompt for re-auth on next launch.",
    )


def clear_teams_cache(username: str) -> dict:
    return _ok(
        "clear_teams_cache",
        f"Cleared %localappdata%\\Packages\\MSTeams_8wekyb3d8bbwe\\LocalCache for {username}. "
        "Teams will rebuild cache on next launch.",
    )


def push_wifi_driver_update(device_id: str) -> dict:
    return _ok(
        "push_wifi_driver_update",
        f"Intel Wi-Fi driver update policy (2026-05 baseline) pushed to device {device_id} via Intune. "
        "Update will apply on next policy sync (~15 min).",
    )


def remap_drives(username: str, department: str = "") -> dict:
    return _ok(
        "remap_drives",
        f"Executed \\\\IT-TOOLS\\Scripts\\map-drives.bat for {username} "
        f"(dept: {department or 'unspecified'}). Drive mappings restored from central config.",
    )


def unlock_ad_account(username: str) -> dict:
    return _ok(
        "unlock_ad_account",
        f"Unlock-ADAccount executed for {username} on LIMMATICA domain. "
        "Account active. Okta sync propagates within ~2 min.",
    )


def enable_onedrive_files_on_demand(username: str) -> dict:
    return _ok(
        "enable_onedrive_files_on_demand",
        f"OneDrive Files On-Demand enabled for {username} via Intune policy. "
        "Full local sync will stop accumulating after next OneDrive restart.",
    )


def push_approved_software(username: str, software_name: str) -> dict:
    return _ok(
        "push_approved_software",
        f"Intune 'Required' assignment created: {software_name} → {username}'s device. "
        "Install will trigger within 15 min on next policy sync. Logged in Intune under device compliance.",
    )


def create_escalation_ticket(
    queue: str, summary: str, priority: str = "P3-Normal"
) -> dict:
    import random
    ticket_num = f"INC{random.randint(1000000, 9999999)}"
    result = _ok(
        "create_escalation_ticket",
        f"Ticket #{ticket_num} opened in {queue} (priority: {priority}). "
        f"On-call technician notified. SLA clock started.",
    )
    result["ticket_number"] = ticket_num
    result["queue"] = queue
    result["priority"] = priority
    return result


REGISTRY: dict[str, callable] = {
    "reset_vpn_profile": reset_vpn_profile,
    "restart_print_spooler": restart_print_spooler,
    "clear_credential_manager": clear_credential_manager,
    "clear_teams_cache": clear_teams_cache,
    "push_wifi_driver_update": push_wifi_driver_update,
    "remap_drives": remap_drives,
    "unlock_ad_account": unlock_ad_account,
    "enable_onedrive_files_on_demand": enable_onedrive_files_on_demand,
    "push_approved_software": push_approved_software,
    "create_escalation_ticket": create_escalation_ticket,
}


def dispatch(tool_name: str, tool_input: dict) -> dict:
    return REGISTRY[tool_name](**tool_input)
