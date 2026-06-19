import argparse
import getpass
import sys
import time
import string
import secrets
import shutil
import pyperclip
import pyotp
from pathlib import Path

from vokul.core import VaultEngine, VaultManager, VaultError

DEFAULT_VAULT_PATH = Path.home() / ".vokul" / "vault.vk"

def main() -> None:
    parser = argparse.ArgumentParser(description="VOKUL: Local-First Secure Password Manager")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT_PATH)
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Core Commands
    subparsers.add_parser("init")
    
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--service", required=True)
    add_parser.add_argument("--totp", help=argparse.SUPPRESS, default=None)
    
    add_totp_parser = subparsers.add_parser("add-totp")
    add_totp_parser.add_argument("--service", required=True)
    
    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("--service", required=True)
    get_parser.add_argument("--show", action="store_true", help="Print password to terminal instead of clipboard")

    # Discovery Commands
    subparsers.add_parser("list")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")

    hist_parser = subparsers.add_parser("history")
    hist_parser.add_argument("--service", required=True)

    # Utilities
    gen_parser = subparsers.add_parser("generate")
    gen_parser.add_argument("--length", type=int, default=16)
    gen_parser.add_argument("--no-symbols", action="store_true")

    totp_parser = subparsers.add_parser("totp")
    totp_parser.add_argument("--service", required=True)

    destruct_parser = subparsers.add_parser("destruct")
    destruct_parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    
    engine = VaultEngine()
    manager = VaultManager(args.vault, engine)

    try:
        if args.command == "init":
            if manager.exists():
                print(f"Error: Vault already exists at {args.vault}", file=sys.stderr)
                sys.exit(1)
            mp = getpass.getpass("Create a strong Master Password: ")
            confirm = getpass.getpass("Confirm Master Password: ")
            if mp != confirm:
                print("Error: Passwords do not match.", file=sys.stderr)
                sys.exit(1)
            manager.create_new_vault(mp)
            print(f"Success: Initialized clean vault database at {args.vault}")

        # Commands that require an unlocked vault
        elif args.command in ("add", "add-totp", "get", "list", "search", "history", "totp"):
            if not manager.exists():
                print("Error: No vault found. Run 'vokul init' first.", file=sys.stderr)
                sys.exit(1)
                
            mp = getpass.getpass("Enter your Master Password: ")
            manager.load_and_decrypt(mp)
            
            if args.command == "add":
                secret = getpass.getpass(f"Enter password for [{args.service}]: ")
                totp_input = input("Enter optional TOTP secret (press Enter to skip): ").strip()
                totp_secret = totp_input if totp_input else None
                manager.set_secret(args.service, secret, totp_secret)
                manager.save()
                print(f"Success: Stored credentials securely for '{args.service}'.")
                
            elif args.command == "add-totp":
                totp_input = input(f"Enter TOTP secret for [{args.service}]: ").strip()
                if not totp_input:
                    print("Error: TOTP secret cannot be empty.", file=sys.stderr)
                    sys.exit(1)
                manager.set_secret(args.service, None, totp_input)
                manager.save()
                print(f"Success: Added TOTP secret securely for '{args.service}'.")
                
            elif args.command == "get":
                secret_dict = manager.get_secret(args.service)
                if secret_dict:
                    if secret_dict.get("pass"):
                        secret = secret_dict["pass"][0]
                        if args.show:
                            print(f"Password for {args.service}: {secret}")
                        else:
                            try:
                                pyperclip.copy(secret)
                                print(f"Success: Password for [{args.service}] copied to clipboard!")
                                for i in range(15, 0, -1):
                                    print(f"Clearing clipboard in {i} seconds...", end="\r")
                                    time.sleep(1)
                                pyperclip.copy("")
                                print("\nSuccess: Clipboard cleared securely.")
                            except Exception as e:
                                print(f"Clipboard Error: {e}. Defaulting to terminal display:")
                                print(f"Password: {secret}")
                    else:
                        print(f"Notice: '{args.service}' does not have a password stored (TOTP-only profile).", file=sys.stderr)
                else:
                    print(f"No entry found for service: '{args.service}'", file=sys.stderr)

            elif args.command == "list":
                services = manager.list_services()
                if services:
                    print("\nStored Services:")
                    for s in services:
                        print(f" - {s}")
                else:
                    print("Vault is empty.")

            elif args.command == "search":
                matches = manager.search_services(args.query)
                if matches:
                    print(f"\nSearch results for '{args.query}':")
                    for m in matches:
                        print(f" - {m}")
                else:
                    print(f"No services found matching '{args.query}'.")

            elif args.command == "history":
                history = manager.get_history(args.service)
                if history:
                    print(f"\nPassword history for '{args.service}':")
                    for idx, pw in enumerate(history):
                        label = "Current" if idx == 0 else f"Old ({idx})"
                        print(f" [{label}] {pw}")
                else:
                    print(f"No history found or service contains only a TOTP profile.")

            elif args.command == "totp":
                secret_dict = manager.get_secret(args.service)
                if secret_dict and secret_dict.get("totp"):
                    try:
                        totp = pyotp.TOTP(secret_dict["totp"])
                        code = totp.now()
                        print(f"TOTP code for {args.service}: {code}")
                        
                        try:
                            pyperclip.copy(code)
                            print("Success: TOTP code copied to clipboard!")
                            for i in range(15, 0, -1):
                                print(f"Clearing clipboard in {i} seconds...", end="\r")
                                time.sleep(1)
                            pyperclip.copy("")
                            print("\nSuccess: Clipboard cleared securely.")
                        except Exception as e:
                            print(f"Clipboard Error: {e}", file=sys.stderr)
                            
                    except Exception as e:
                        print(f"Error generating TOTP: {e}", file=sys.stderr)
                else:
                    print(f"No TOTP secret found for service: '{args.service}'", file=sys.stderr)

        # Generate command
        elif args.command == "generate":
            chars = string.ascii_letters + string.digits
            if not args.no_symbols:
                chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
            generated_password = "".join(secrets.choice(chars) for _ in range(args.length))
            
            print("-" * 40)
            print(f"Generated Password: {generated_password}")
            print("-" * 40)
            
            try:
                pyperclip.copy(generated_password)
                print("Copied to clipboard automatically!")
            except:
                pass

            save_choice = input("\nWould you like to save this password to a service? (y/N): ").strip().lower()
            if save_choice in ("y", "yes"):
                if not manager.exists():
                    print("Error: No vault found. Run 'vokul init' first.", file=sys.stderr)
                    sys.exit(1)
                
                service = input("Enter the service name: ").strip()
                if not service:
                    print("Error: Service name cannot be empty.", file=sys.stderr)
                    sys.exit(1)
                
                totp_opt = input("Enter optional TOTP secret (press Enter to skip): ").strip()
                totp_secret = totp_opt if totp_opt else None
                
                mp = getpass.getpass("Enter your Master Password to unlock and save: ")
                manager.load_and_decrypt(mp)
                manager.set_secret(service, generated_password, totp_secret)
                manager.save()
                print(f"Success: Stored generated credentials securely for '{service}'.")

        # Destruct command
        elif args.command == "destruct":
            vault_dir = args.vault.parent
            print("!" * 50)
            print("WARNING: This will permanently delete your entire password vault!")
            print(f"Target directory: {vault_dir}")
            print("This action is completely IRREVERSIBLE.")
            print("!" * 50)
            
            if not args.force:
                confirmation = input("\nTo proceed, type 'DESTROY' in all capital letters: ")
                if confirmation != "DESTROY":
                    print("Aborting destruction. Your data is safe.")
                    sys.exit(0)
                    
            if vault_dir.exists() and vault_dir.is_dir():
                shutil.rmtree(vault_dir)
                print(f"\nSuccess: Completely erased {vault_dir}")
            elif args.vault.exists():
                args.vault.unlink()
                print(f"\nSuccess: Completely erased {args.vault}")
            else:
                print("\nNo VOKUL data found to erase. System is already clean.")
                
        else:
            parser.print_help()

    except VaultError as err:
        print(f"Security Error: {err}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()