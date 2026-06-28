import argparse
import sys
import time
import string
import secrets
import json
import os
import pyperclip
import pyotp
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from vokul.core import VaultEngine, VaultManager, VaultError

VERSION = "1.0.0"
DEFAULT_VAULT_PATH = Path("vault.vk")

console = Console()

ASCII_ART = """[bold purple]
▄▄▄▄  ▄▄▄▄   ▄▄▄▄▄   ▄▄▄   ▄▄▄ ▄▄▄  ▄▄▄ ▄▄▄          ▄▄▄▄▄▄▄ ▄▄▄      ▄▄▄▄▄ 
▀███  ███▀ ▄███████▄ ███ ▄███▀ ███  ███ ███         ███▀▀▀▀▀ ███       ███  
 ███  ███  ███   ███ ███████   ███  ███ ███         ███      ███       ███  
 ███▄▄███  ███▄▄▄███ ███▀███▄  ███▄▄███ ███         ███      ███       ███  
  ▀████▀    ▀█████▀  ███  ▀███ ▀██████▀ ████████    ▀███████ ████████ ▄███▄ 
[/bold purple]"""

def get_lock_path(vault_path: Path) -> Path:
    """Returns the path for the hidden companion security lock file."""
    return vault_path.parent / f".{vault_path.name}.lock"

def enforce_persistent_throttling(lock_path: Path, is_json: bool):
    """Checks the lock file across separate CLI calls to block brute-forcing."""
    if not lock_path.exists():
        return
    try:
        with open(lock_path, "r") as f:
            data = json.load(f)
        failures = data.get("failures", [])
        
        # Filter to only count failures that happened within the last 5 minutes
        now = time.time()
        failures = [t for t in failures if now - t < 300]
        
        if len(failures) >= 3:
            # Progressive scaling penalty: 15 seconds base + 10s per extra offense
            penalty = 15 + (len(failures) - 3) * 10
            
            if is_json:
                print(json.dumps({"error": f"Security Lockout Active. Cooldown remaining: {penalty}s", "type": "ThrottlingError"}))
                sys.exit(1)
                
            console.print(Panel(f"[bold red]🚨 PERSISTENT SECURITY LOCKOUT ACTIVE[/bold red]\n"
                                f"Too many recent bad attempts detected across terminal sessions.\n"
                                f"The system will stall to protect your vault data.", border_style="red"))
            with console.status(f"[bold red]Lockdown enforced. Throttling process for {penalty}s...[/bold red]", spinner="bouncingBar"):
                time.sleep(penalty)
    except Exception:
        pass # Protect operational continuity if lock file is corrupted

def record_failure(lock_path: Path):
    """Persistently saves a failed attempt timestamp to disk."""
    failures = []
    if lock_path.exists():
        try:
            with open(lock_path, "r") as f:
                data = json.load(f)
            failures = data.get("failures", [])
        except Exception:
            pass
    failures.append(time.time())
    try:
        with open(lock_path, "w") as f:
            json.dump({"failures": failures}, f)
    except Exception:
        pass

def clear_lock_state(lock_path: Path):
    """Safely drops the lock file after successful auth or complete vault destruction."""
    if lock_path.exists():
        try:
            lock_path.unlink()
        except Exception:
            pass

def get_master_password(is_json: bool, attempt_num: int = 1) -> str:
    """Fetches password from environment or uses Rich secure prompt with attempt counter."""
    mp = os.environ.get("VOKUL_MASTER_PASSWORD")
    if mp:
        return mp
    if is_json:
        print(json.dumps({"error": "VOKUL_MASTER_PASSWORD environment variable not set.", "type": "AuthError"}))
        sys.exit(1)
        
    prompt_msg = "[bold cyan]Enter your Master Password[/bold cyan]"
    if attempt_num > 1:
        prompt_msg = f"[bold yellow](Session Attempt {attempt_num}/3)[/bold yellow] {prompt_msg}"
        
    return Prompt.ask(prompt_msg, password=True)

def print_banner():
    console.print(ASCII_ART)

def main() -> None:
    parser = argparse.ArgumentParser(description="VOKUL: Local-First Secure Password Manager")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT_PATH)
    parser.add_argument("--json", action="store_true", help="Output results as JSON (suppresses TUI)")
    
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("init")
    subparsers.add_parser("check")
    subparsers.add_parser("version")
    
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--service", required=True)
    add_parser.add_argument("--password", help="Specify password directly")
    add_parser.add_argument("--totp", help="Specify TOTP secret directly")
    
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
    lock_path = get_lock_path(args.vault)

    try:
        if args.command == "version":
            if args.json:
                print(json.dumps({"version": VERSION, "api_ready": True}))
            else:
                print_banner()
                console.print(Panel(f"VOKUL Core Engine - Version [bold green]{VERSION}[/bold green]", expand=False))
            return

        elif args.command == "check":
            # Bug Fix: Check structural path directly instead of relying on early side-effecting manager
            exists = args.vault.exists()
            if args.json:
                print(json.dumps({"command": "check", "vault_exists": exists, "vault_path": str(args.vault)}))
            else:
                print_banner()
                if exists:
                    console.print(f" [bold green]✔[/bold green] Vault found and accessible at: [cyan]{args.vault}[/cyan]\n")
                else:
                    console.print(f" [bold red]✖[/bold red] No vault found at: [cyan]{args.vault}[/cyan]\n")
            return

        elif args.command == "init":
            # Bug Fix: Validate pristine path state before creating manager to eliminate ghost file bugs
            if args.vault.exists():
                if args.json: print(json.dumps({"error": "Vault already exists"}))
                else: console.print(f"[bold red]Error:[/bold red] Vault already exists at {args.vault}")
                sys.exit(1)
                
            mp = get_master_password(args.json)
            if not args.json:
                confirm = Prompt.ask("[bold cyan]Confirm Master Password[/bold cyan]", password=True)
                if mp != confirm:
                    console.print("[bold red]Error:[/bold red] Passwords do not match.")
                    sys.exit(1)
            
            manager = VaultManager(args.vault, engine)
            manager.create_new_vault(mp)
            clear_lock_state(lock_path)
            
            if args.json: print(json.dumps({"status": "success"}))
            else: console.print(f"[bold green]✔ Success:[/bold green] Initialized clean vault database at [cyan]{args.vault}[/cyan]")

        elif args.command in ("add", "edit", "delete", "get", "list", "search", "history", "totp", "export"):
            if not args.vault.exists():
                if args.json: print(json.dumps({"error": "No vault found."}))
                else: console.print("[bold red]Error:[/bold red] No vault found. Run 'vokul init' first.")
                sys.exit(1)
            
            # Persistent check across distinct command invocations
            enforce_persistent_throttling(lock_path, args.json)
            
            manager = VaultManager(args.vault, engine)
            max_attempts = 3
            authenticated = False
            
            for attempt in range(1, max_attempts + 1):
                mp = get_master_password(args.json, attempt_num=attempt)
                try:
                    if not args.json:
                        with console.status("[bold blue]Decrypting vault...", spinner="dots"):
                            manager.load_and_decrypt(mp)
                    else:
                        manager.load_and_decrypt(mp)
                    authenticated = True
                    clear_lock_state(lock_path) # Wipe record clean on a successful auth match
                    break 
                except VaultError as err:
                    record_failure(lock_path) # Lock it down persistently on disk
                    if args.json:
                        print(json.dumps({"error": str(err), "type": "VaultError"}))
                        sys.exit(1)
                        
                    remaining = max_attempts - attempt
                    if remaining > 0:
                        console.print(f"[bold red]❌ Incorrect password.[/bold red] Remaining attempts: [bold yellow]{remaining}[/bold yellow]\n")
                    else:
                        console.print(Panel("[bold red]🚨 ACCESS DENIED: 3 Incorrect Password Attempts.[/bold red]", border_style="red"))
                        # Double-check local execution throttling penalty
                        enforce_persistent_throttling(lock_path, args.json)
                        sys.exit(1)
            
            # --- COMMAND EXECUTIONS ---
            if args.command in ("add", "edit"):
                password = args.password
                if not password:
                    password = Prompt.ask(f"[bold green]Enter password for [{args.service}][/bold green]", password=True)
                
                totp_secret = args.totp
                if not totp_secret and not args.json:
                    totp_secret = Prompt.ask("[bold yellow]Enter optional TOTP secret (press Enter to skip)[/bold yellow]", default="")
                    totp_secret = totp_secret if totp_secret else None
                
                manager.set_secret(args.service, password, totp_secret)
                manager.save()
                
                if args.json: print(json.dumps({"status": "success", "service": args.service}))
                else: console.print(f"[bold green]✔ Success:[/bold green] Stored credentials securely for '[cyan]{args.service}[/cyan]'.")
                
            elif args.command == "delete":
                secret_dict = manager.get_secret(args.service)
                if not secret_dict:
                    if args.json: print(json.dumps({"error": "Service not found"}))
                    else: console.print(f"[bold red]Error:[/bold red] Service '{args.service}' does not exist.")
                    sys.exit(1)
                    
                if args.json:
                    manager.delete_secret(args.service)
                    manager.save()
                    print(json.dumps({"status": "success", "action": "deleted"}))
                else:
                    if Confirm.ask(f"[bold red]Are you sure you want to completely delete '{args.service}'?[/bold red]"):
                        manager.delete_secret(args.service)
                        manager.save()
                        console.print(f"[bold green]✔ Success:[/bold green] Purged entry '{args.service}' from database safely.")
                    else:
                        console.print("[dim]Action cancelled.[/dim]")

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
                                console.print(Panel(f"[bold white]{password}[/bold white]", title=f"Password for {args.service}", expand=False, border_style="green"))
                            else:
                                try:
                                    pyperclip.copy(password)
                                    console.print(f"[bold green]✔ Success:[/bold green] Password for [[cyan]{args.service}[/cyan]] copied to clipboard!")
                                    
                                    with console.status("[bold yellow]Clipboard active. Clearing in 15 seconds...[/bold yellow]", spinner="bouncingBar"):
                                        time.sleep(15)
                                        
                                    pyperclip.copy("")
                                    console.print("[bold green]✔ Success:[/bold green] Clipboard cleared securely.")
                                except Exception as e:
                                    console.print(f"[bold red]Clipboard Error:[/bold red] {e}")
                                    console.print(Panel(f"[bold white]{password}[/bold white]", title=f"Fallback Display", expand=False))
                        else:
                            console.print(f"[yellow]Notice:[/yellow] '{args.service}' does not have a password stored (TOTP-only profile).")
                else:
                    if args.json: print(json.dumps({"error": "Service not found"}))
                    else: console.print(f"[bold red]Error:[/bold red] No entry found for service: '{args.service}'")

            elif args.command == "list":
                services = manager.list_services()
                if args.json: print(json.dumps({"services": services}))
                else:
                    if services:
                        table = Table(title="[bold purple]VOKUL Vault Entries[/bold purple]")
                        table.add_column("Service Name", style="cyan", no_wrap=True)
                        table.add_column("MFA/TOTP", justify="center")

                        for s in services:
                            sec = manager.get_secret(s)
                            mfa_status = "[green]✔ Active[/green]" if sec.get("totp") else "[dim]None[/dim]"
                            table.add_row(s, mfa_status)
                            
                        console.print(table)
                    else:
                        console.print(Panel("[yellow]Vault is currently empty.[/yellow]", expand=False))

            elif args.command == "search":
                matches = manager.search_services(args.query)
                if args.json: print(json.dumps({"matches": matches}))
                else:
                    if matches:
                        table = Table(title=f"Search Results for: [yellow]'{args.query}'[/yellow]")
                        table.add_column("Matched Service", style="cyan")
                        for m in matches: table.add_row(m)
                        console.print(table)
                    else:
                        console.print(f"[yellow]No services found matching '{args.query}'.[/yellow]")

            elif args.command == "totp":
                secret_dict = manager.get_secret(args.service)
                if secret_dict and secret_dict.get("totp"):
                    totp_code = pyotp.TOTP(secret_dict["totp"]).now()
                    if args.json: print(json.dumps({"totp": totp_code}))
                    else:
                        console.print(Panel(f"[bold cyan]{totp_code[:3]} {totp_code[3:]}[/bold cyan]", title=f"TOTP: {args.service}", expand=False, border_style="blue"))
                else:
                    if args.json: print(json.dumps({"error": "No TOTP config"}))
                    else: console.print(f"[bold red]Error:[/bold red] No TOTP profile active for '{args.service}'")

            elif args.command == "history":
                history = manager.get_history(args.service)
                if args.json: print(json.dumps({"history": history}))
                else:
                    if history:
                        table = Table(title=f"Password History: [cyan]{args.service}[/cyan]")
                        table.add_column("Age", justify="center", style="dim")
                        table.add_column("Password", style="white")
                        
                        for idx, pwd in enumerate(history):
                            label = "Current" if idx == 0 else f"{idx} changes ago"
                            table.add_row(label, pwd)
                        console.print(table)
                    else:
                        console.print(f"[yellow]No password history tracked for '{args.service}'.[/yellow]")

        elif args.command == "generate":
            if args.memorable:
                words = ["correct", "horse", "battery", "staple", "vibe", "crypto", "vault", "cyber", "secure", "python"]
                password = "-".join(secrets.choice(words) for _ in range(4))
            else:
                chars = string.ascii_letters + string.digits
                if not args.no_symbols:
                    chars += "!@#$%^&*"
                password = "".join(secrets.choice(chars) for _ in range(args.length))
                
            if args.json: print(json.dumps({"generated": password}))
            else: console.print(Panel(f"[bold green]{password}[/bold green]", title="Generated Password", expand=False))

        elif args.command == "destruct":
            if args.json:
                if args.force:
                    if args.vault.exists(): args.vault.unlink()
                    clear_lock_state(lock_path)
                    print(json.dumps({"status": "vaporized"}))
                else:
                    print(json.dumps({"error": "Requires --force in JSON mode."}))
            else:
                if not args.force:
                    console.print(Panel("[bold red]WARNING: This will permanently vaporize your entire vault database.[/bold red]", border_style="red"))
                    confirm = Prompt.ask("Type [bold red]DESTROY[/bold red] to proceed")
                    if confirm != "DESTROY":
                        console.print("[dim]Aborted.[/dim]")
                        sys.exit(0)
                if args.vault.exists():
                    args.vault.unlink()
                clear_lock_state(lock_path) # Purge failure locks too so a clean state is guaranteed
                console.print("💥 [bold red]Success:[/bold red] Vault database completely shredded from disk.")

        elif not args.command:
            print_banner()
            parser.print_help()

    except Exception as e:
        if hasattr(args, 'json') and args.json:
            print(json.dumps({"error": str(e), "type": "SystemError"}))
        else:
            console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        if not (hasattr(args, 'json') and args.json):
            console.print("\n[dim]Operation cancelled.[/dim]")
        sys.exit(1)

if __name__ == "__main__":
    main()