import sys
from pathlib import Path

# Windows konsolida UTF-8 chiqishini ta'minlash
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.compiler import compile_file
from src.vm import VirtualMachine

VERSION = "0.6.0"


def run_check(source_path: str):
    """Statik tahlil (--check) rejimi: JSON diagnostika chiqaradi."""
    from src.analyzer import main_check
    main_check(source_path)


def run_build(source_path: str, output_path: str = None) -> str:
    src_file = Path(source_path)
    if not src_file.exists():
        print(f"[XATO] Manba fayli topilmadi: {source_path}")
        sys.exit(1)

    print(f"[*] Kompilyatsiya qilinmoqda: {source_path}")

    # Agar chiqish ko'rsatilmagan bo'lsa: build/<stem>.flowc
    if output_path is None:
        build_dir = Path("build")
        build_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(build_dir / f"{src_file.stem}.flowc")

    out_path = compile_file(str(src_file), output_path)
    file_size = Path(out_path).stat().st_size
    print(f"[+] Muvaffaqiyatli saqlandi: {out_path} ({file_size} bayt, siqilgan binary)")
    return out_path


def run_vm(target_path: str):
    p = Path(target_path)

    # Agar berilgan fayl .flw bo'lsa yoki to'g'ridan-to'g'ri topilmasa:
    if p.suffix == ".flw":
        # Avval build qilib, keyin ishga tushirish
        target_path = run_build(str(p))
        p = Path(target_path)
    elif not p.exists():
        # build/ ichidan qidirib ko'rish
        alt_path = Path("build") / p.name
        if alt_path.exists():
            p = alt_path
        else:
            print(f"[XATO] Bayt-kod fayli topilmadi: {target_path} (shuningdek {alt_path} ham mavjud emas)")
            sys.exit(1)

    print(f"[*] Flow VM ishga tushmoqda: {p}")
    print("=" * 40)
    vm = VirtualMachine()
    bytecode = vm.load_bytecode(p)
    vm.run_bytecode(bytecode)
    print("=" * 40)
    print("[+] Dastur muvaffaqiyatli yakunlandi.")


def print_help():
    print(f"Flow Programming Language CLI (v{VERSION})")
    print("\nFoydalanish:")
    print("  flow <fayl.flw>                    Faylni build/ ichiga kompilatsiya qilib, VM'da ishga tushiradi")
    print("  flow <fayl.flw> --verbose, -v      Vizual rejim: Lexer, AST, Bytecode va VM runtime bosqichlarini ko'rsatadi")
    print("  flow compile|build <fayl.flw> [out] Manba kodni build/<fayl>.flowc binary bayt-kodga aylantiradi")
    print("  flow run <fayl.flowc | fayl.flw>   Bayt-kodni Flow VM'da bajaradi")
    print("  flow --version, -V                 Versiyani ko'rsatadi")
    print("  flow --help, -h                    Ushbu yordam matnini ko'rsatadi")


def main():
    args = sys.argv[1:]

    if not args:
        print_help()
        return

    # Faqat bitta argument berilgan va u yordam yoki versiya bo'lsa
    if len(args) == 1:
        if args[0] in ("--help", "-h", "help"):
            print_help()
            return
        if args[0] in ("--version", "-V", "-v", "version"):
            print(f"Flow Language v{VERSION}")
            return

    # Verbose bayrog'i mavjudligini aniqlash
    is_verbose = False
    clean_args = []
    for arg in args:
        if arg in ("--verbose", "-v"):
            is_verbose = True
        else:
            clean_args.append(arg)

    if not clean_args:
        print_help()
        return

    command = clean_args[0]

    if command in ("--help", "-h", "help"):
        print_help()
        return

    if command in ("--version", "-V", "version"):
        print(f"Flow Language v{VERSION}")
        return

    if command == "--check":
        if len(clean_args) < 2:
            print("Foydalanish: flow --check <fayl.flw>")
            sys.exit(1)
        run_check(clean_args[1])
        return

    if is_verbose:
        from src.visualizer import run_verbose_pipeline
        # Agar buyruq 'run' bo'lsa: flow run demo.flw -v
        if command == "run":
            if len(clean_args) < 2:
                print("Foydalanish: flow run <fayl.flw> --verbose")
                sys.exit(1)
            source = clean_args[1]
        elif command in ("build", "compile"):
            if len(clean_args) < 2:
                print(f"Foydalanish: flow {command} <fayl.flw> --verbose")
                sys.exit(1)
            source = clean_args[1]
        else:
            source = command

        output = clean_args[1] if (len(clean_args) > 1 and command not in ("run", "build", "compile")) else (clean_args[2] if len(clean_args) > 2 else None)
        run_verbose_pipeline(source, output)
        return

    if command in ("build", "compile"):
        if len(clean_args) < 2:
            print(f"Foydalanish: flow {command} <fayl.flw> [chiqish.flowc]")
            sys.exit(1)
        source = clean_args[1]
        output = clean_args[2] if len(clean_args) > 2 else None
        run_build(source, output)

    elif command == "run":
        if len(clean_args) < 2:
            print("Foydalanish: flow run <fayl.flowc | fayl.flw>")
            sys.exit(1)
        target = clean_args[1]
        run_vm(target)

    else:
        # Fayl berilgan bo'lsa (masalan: flow hello.flw): avval build/, keyin run
        source = command
        flowc_path = run_build(source)
        print()
        run_vm(flowc_path)


if __name__ == "__main__":
    main()
