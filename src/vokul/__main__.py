import argparse
import getpass
import sys
import time
import string
import secrets
import shutil
import json
import os
import pyperclip
import pyotp
from pathlib import Path

from vokul.core import VaultEngine, VaultManager, VaultError

VERSION = "1.0.0"

# ANSI Escape Sequences for Purple Text
PURPLE = "\033[95m"
RESET = "\033[0m"

ASCII_ART = f"""{PURPLE}
▄▄▄▄  ▄▄▄▄   ▄▄▄▄▄   ▄▄▄   ▄▄▄ ▄▄▄  ▄▄▄ ▄▄▄          ▄▄▄▄▄▄▄ ▄▄▄      ▄▄▄▄▄ 
▀███  ███▀ ▄███████▄ ███ ▄███▀ ███  ███ ███         ███▀▀▀▀▀ ███       ███  
 ███  ███  ███   ███ ███████   ███  ███ ███         ███      ███       ███  
 ███▄▄███  ███▄▄▄███ ███▀███▄  ███▄▄███ ███         ███      ███       ███  
  ▀████▀    ▀█████▀  ███  ▀███ ▀██████▀ ████████    ▀███████ ████████ ▄███▄ 
{RESET}"""

DEFAULT_VAULT_PATH = Path("vault.vk")

def get_master_password(is_json: bool) -> str:
    """Fetches password from environment for silent integration, or prompts human."""
    mp = os.environ.get("VOKUL_MASTER_PASSWORD")
    if mp:
        return mp
    if is_json:
        print(json.dumps({"error": "Integration Mode Active: VOKUL_MASTER_PASSWORD environment variable not set.", "type": "AuthError"}))
        sys.exit(1)
    return getpass.getpass("Enter your Master Password: ")

def main() -> None:
    parser = argparse.ArgumentParser(description="VOKUL: Local-First Secure Password Manager")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT_PATH)
    parser.add_argument("--json", action="store_true", help="Output results as JSON for API integrations")
    
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("init")
    subparsers.add_parser("check")
    subparsers.add_parser("version")
    
    # Upgraded to allow non-interactive execution via parameters for extensions
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--service", required=True)
    add_parser.add_argument("--password", help="Specify password directly (non-interactive)")
    add_parser.add_argument("--totp", help="Specify TOTP secret directly (non-interactive)")
    
    edit_parser = subparsers.add_parser("edit")
    edit_parser.add_argument("--service", required=True)
    edit_parser.add_argument("--password", help="Specify new password directly")
    edit_parser.add_argument("--totp", help="Specify new TOTP secret directly")
    
    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("--service", required=True)
    
    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("--service", required=True)
    get_parser.add_argument("--show", action="store_true", help="Print password to terminal instead of clipboard")

    subparsers.add_parser("list")
    subparsers.add_parser("export")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")

    hist_parser = subparsers.add_parser("history")
    hist_parser.add_argument("--service", required=True)

    gen_parser = subparsers.add_parser("generate")
    gen_parser.add_argument("--length", type=int, default=16)
    gen_parser.add_argument("--no-symbols", action="store_true")
    gen_parser.add_argument("--memorable", action="store_true", help="Generate a phrase-based memorable password")

    totp_parser = subparsers.add_parser("totp")
    totp_parser.add_argument("--service", required=True)

    destruct_parser = subparsers.add_parser("destruct")
    destruct_parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    
    engine = VaultEngine()
    manager = VaultManager(args.vault, engine)

    try:
        if args.command == "version":
            if args.json:
                print(json.dumps({"version": VERSION, "api_ready": True}))
            else:
                print(ASCII_ART)
                print(f" VOKUL Core Engine - Version {VERSION}\n")
            return

        elif args.command == "check":
            exists = manager.exists()
            if args.json:
                print(json.dumps({"command": "check", "vault_exists": exists, "vault_path": str(args.vault)}))
            else:
                print(ASCII_ART)
                if exists:
                    print(f" ✅ Vault found and accessible at: {args.vault}\n")
                else:
                    print(f" ❌ No vault found at: {args.vault}\n")
            return

        elif args.command == "init":
            if manager.exists():
                if args.json:
                    print(json.dumps({"error": "Vault already exists"}))
                else:
                    print(f"Error: Vault already exists at {args.vault}", file=sys.stderr)
                sys.exit(1)
                
            mp = get_master_password(args.json)
            if not args.json:
                confirm = getpass.getpass("Confirm Master Password: ")
                if mp != confirm:
                    print("Error: Passwords do not match.", file=sys.stderr)
                    sys.exit(1)
                    
            manager.create_new_vault(mp)
            if args.json:
                print(json.dumps({"status": "success", "message": "Vault initialized"}))
            else:
                print(f"Success: Initialized clean vault database at {args.vault}")

        elif args.command in ("add", "edit", "delete", "get", "list", "search", "history", "totp", "export"):
            if not manager.exists():
                if args.json:
                    print(json.dumps({"error": "No vault found. Initialization required."}))
                else:
                    print("Error: No vault found. Run 'vokul init' first.", file=sys.stderr)
                sys.exit(1)
                
            mp = get_master_password(args.json)
            manager.load_and_decrypt(mp)
            
            if args.command in ("add", "edit"):
                # Determine password source
                password = args.password
                if not password:
                    if args.json:
                        print(json.dumps({"error": "Non-interactive write requires --password parameter."}))
                        sys.exit(1)
                    password = getpass.getpass(f"Enter password for [{args.service}]: ")
                
                # Determine TOTP source
                totp_secret = args.totp
                if not totp_secret and not args.json:
                    totp_input = input("Enter optional TOTP secret (press Enter to skip): ").strip()
                    totp_secret = totp_input if totp_input else None
                
                manager.set_secret(args.service, password, totp_secret)
                manager.save()
                
                if args.json:
                    print(json.dumps({"status": "success", "action": args.command, "service": args.service}))
                else:
                    print(f"Success: Stored credentials securely for '{args.service}'.")
                
            elif args.command == "delete":
                secret_dict = manager.get_secret(args.service)
                if not secret_dict:
                    if args.json: print(json.dumps({"error": "Service not found"}))
                    else: print(f"Error: Service '{args.service}' does not exist.", file=sys.stderr)
                    sys.exit(1)
                    
                if args.json:
                    manager.delete_secret(args.service)
                    manager.save()
                    print(json.dumps({"status": "success", "action": "deleted", "service": args.service}))
                else:
                    confirm = input(f"Are you sure you want to completely delete '{args.service}'? (y/N): ").strip().lower()
                    if confirm in ("y", "yes"):
                        manager.delete_secret(args.service)
                        manager.save()
                        print(f"Success: Purged entry '{args.service}' from database safely.")
                    else:
                        print("Action cancelled.")

            elif args.command == "get":
                secret_dict = manager.get_secret(args.service)
                if secret_dict:
                    password = secret_dict.get("pass", [None])[0]
                    totp_secret = secret_dict.get("totp")
                    totp_code = pyotp.TOTP(totp_secret).now() if totp_secret else None

                    if args.json:
                        payload = {"service": args.service}
                        if password: payload["password"] = password
                        if totp_code: payload["totp"] = totp_code
                        print(json.dumps(payload))
                    else:
                        if password:
                            if args.show:
                                print(f"Password for {args.service}: {password}")
                            else:
                                try:
                                    pyperclip.copy(password)
                                    print(f"Success: Password for [{args.service}] copied to clipboard!")
                                    for i in range(15, 0, -1):
                                        print(f"Clearing clipboard in {i} seconds...", end="\r")
                                        time.sleep(1)
                                    pyperclip.copy("")
                                    print("\nSuccess: Clipboard cleared securely.")
                                except Exception as e:
                                    print(f"Clipboard Error: {e}. Defaulting to terminal display:")
                                    print(f"Password: {password}")
                        else:
                            print(f"Notice: '{args.service}' does not have a password stored (TOTP-only profile).", file=sys.stderr)
                else:
                    if args.json: print(json.dumps({"error": "Service not found"}))
                    else: print(f"No entry found for service: '{args.service}'", file=sys.stderr)

            elif args.command == "list":
                services = manager.list_services()
                if args.json:
                    print(json.dumps({"services": services}))
                else:
                    if services:
                        print("\nStored Services:")
                        for s in services: print(f" - {s}")
                    else:
                        print("Vault is empty.")

            elif args.command == "search":
                matches = manager.search_services(args.query)
                if args.json:
                    print(json.dumps({"query": args.query, "matches": matches}))
                else:
                    if matches:
                        print(f"\nSearch results for '{args.query}':")
                        for m in matches: print(f" - {m}")
                    else:
                        print(f"No services found matching '{args.query}'.")

            elif args.command == "totp":
                secret_dict = manager.get_secret(args.service)
                if secret_dict and secret_dict.get("totp"):
                    totp_code = pyotp.TOTP(secret_dict["totp"]).now()
                    if args.json:
                        print(json.dumps({"service": args.service, "totp": totp_code}))
                    else:
                        print(f"Current TOTP token for {args.service}: {totp_code}")
                else:
                    if args.json: print(json.dumps({"error": "No TOTP config found for this service"}))
                    else: print(f"Error: No TOTP profile active for '{args.service}'", file=sys.stderr)

            elif args.command == "history":
                history = manager.get_history(args.service)
                if args.json:
                    print(json.dumps({"service": args.service, "history": history}))
                else:
                    if history:
                        print(f"\nPassword history for '{args.service}' (Newest first):")
                        for idx, pwd in enumerate(history, 1): print(f" [{idx}] {pwd}")
                    else:
                        print(f"No password history tracked for '{args.service}'.")

            elif args.command == "export":
                data = manager.export_vault_data()
                if args.json:
                    print(json.dumps({"vault_data": data}))
                else:
                    print(json.dumps(data, indent=2))

        elif args.command == "generate":
            if args.memorable:
                words = ["correct", "horse", "battery", "staple", "vibe", "crypto", "vault", "cyber", "secure", "python"]
                password = "-".join(secrets.choice(words) for _ in range(4))
            else:
                chars = string.ascii_letters + string.digits
                if not args.no-symbols:
                    chars += "!@#$%^&*"
                password = "".join(secrets.choice(chars) for _ in range(args.length))
                
            if args.json:
                print(json.dumps({"generated_password": password}))
            else:
                print(f"Generated Password: {password}")

        elif args.command == "destruct":
            if args.json:
                if args.force:
                    if args.vault.exists(): args.vault.unlink()
                    print(json.dumps({"status": "success", "message": "Vault vaporized completely."}))
                else:
                    print(json.dumps({"error": "Destruct command requires --force in JSON mode."}))
            else:
                if not args.force:
                    confirm = input("⚠️ WARNING: This will permanently vaporize your entire vault database. Proceed? (type 'DESTROY'): ")
                    if confirm != "DESTROY":
                        print("Aborted.")
                        sys.exit(0)
                if args.vault.exists():
                    args.vault.unlink()
                print("💥 Success: Vault database completely shredded and removed from disk.")

        elif not args.command:
            print(ASCII_ART)
            parser.print_help()

    except VaultError as err:
        if hasattr(args, 'json') and args.json:
            print(json.dumps({"error": str(err), "type": "VaultError"}))
        else:
            print(f"Security Error: {err}", file=sys.stderr)
            print("Enforcing secure throttling system penalty cooldown... Please wait.", file=sys.stderr)
            time.sleep(2.5)
        sys.exit(1)
    except Exception as e:
        if hasattr(args, 'json') and args.json:
            print(json.dumps({"error": str(e), "type": "SystemError"}))
        else:
            print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        if not (hasattr(args, 'json') and args.json):
            print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()