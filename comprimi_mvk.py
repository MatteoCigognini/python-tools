#!/usr/bin/env python3
"""
Comprime video MKV mantenendo una qualità visivamente identica all'originale.

Requisiti: FFmpeg installato e nel PATH (https://ffmpeg.org/download.html)

Esempi:
    python comprimi_mkv.py film.mkv
    python comprimi_mkv.py film.mkv -o film_compresso.mkv --crf 20
    python comprimi_mkv.py cartella_video/ --codec av1
    python comprimi_mkv.py film.mkv --lossless
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Impostazioni predefinite per codec
CODEC_PRESETS = {
    # H.265: ottimo compromesso, molto compatibile
    "x265": {"encoder": "libx265", "crf": 20, "preset": "slow",
             "extra": ["-x265-params", "log-level=error"]},
    # AV1: file più piccoli, codifica più lenta
    "av1": {"encoder": "libsvtav1", "crf": 28, "preset": "6",
            "extra": ["-svtav1-params", "tune=0"]},
    # H.264: massima compatibilità, compressione minore
    "x264": {"encoder": "libx264", "crf": 18, "preset": "slow", "extra": []},
}


def controlla_ffmpeg():
    if not shutil.which("ffmpeg"):
        sys.exit("Errore: FFmpeg non trovato. Installalo e aggiungilo al PATH.")


def dimensione_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def costruisci_comando(inp: Path, out: Path, codec: str, crf: int | None,
                       preset: str | None, lossless: bool, audio: str) -> list[str]:
    cfg = CODEC_PRESETS[codec]
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(inp),
           # Mantiene TUTTI i flussi: video, tracce audio, sottotitoli, allegati, capitoli
           "-map", "0", "-map_metadata", "0", "-map_chapters", "0",
           "-c:v", cfg["encoder"]]

    if lossless:
        # Senza alcuna perdita (bit-per-bit): il file spesso NON diventa più piccolo
        if codec == "x265":
            cmd += ["-x265-params", "lossless=1:log-level=error"]
        elif codec == "x264":
            cmd += ["-qp", "0"]
        else:
            sys.exit("La modalità --lossless è supportata solo con x265 o x264.")
        cmd += ["-preset", preset or "slow"]
    else:
        cmd += ["-crf", str(crf if crf is not None else cfg["crf"]),
                "-preset", preset or cfg["preset"]] + cfg["extra"]

    # 10 bit: riduce il banding e migliora l'efficienza a parità di qualità
    cmd += ["-pix_fmt", "yuv420p10le"]

    # Audio: copiato senza ricodifica (nessuna perdita) oppure convertito in Opus
    if audio == "copy":
        cmd += ["-c:a", "copy"]
    else:
        cmd += ["-c:a", "libopus", "-b:a", audio]

    # Sottotitoli e allegati (font ecc.) copiati così come sono
    cmd += ["-c:s", "copy", "-c:t", "copy", str(out)]
    return cmd


def comprimi(inp: Path, out: Path, args) -> bool:
    print(f"\n▶ {inp.name}  ({dimensione_mb(inp):.1f} MB)")
    cmd = costruisci_comando(inp, out, args.codec, args.crf,
                             args.preset, args.lossless, args.audio)
    try:
        subprocess.run(cmd + ["-stats", "-loglevel", "error"], check=True)
    except subprocess.CalledProcessError:
        print(f"✗ Errore durante la compressione di {inp.name}")
        if out.exists():
            out.unlink()
        return False

    prima, dopo = dimensione_mb(inp), dimensione_mb(out)
    risparmio = (1 - dopo / prima) * 100
    print(f"✓ {out.name}: {prima:.1f} MB → {dopo:.1f} MB ({risparmio:+.1f}% risparmiato)")
    if dopo >= prima:
        print("  ⚠ Il file non è più piccolo: l'originale era già ben compresso.")
    return True


def main():
    p = argparse.ArgumentParser(description="Comprime video MKV senza perdita di qualità visibile.")
    p.add_argument("input", type=Path, help="File .mkv o cartella contenente file .mkv")
    p.add_argument("-o", "--output", type=Path,
                   help="File o cartella di output (default: *_compresso.mkv accanto all'originale)")
    p.add_argument("--codec", choices=CODEC_PRESETS, default="x265",
                   help="Codec video (default: x265)")
    p.add_argument("--crf", type=int,
                   help="Qualità: più basso = migliore e più pesante "
                        "(default x265=20, x264=18, av1=28)")
    p.add_argument("--preset", help="Velocità di codifica (es. medium, slow, veryslow; per av1: 0-13)")
    p.add_argument("--lossless", action="store_true",
                   help="Compressione matematicamente senza perdita (file spesso più grandi)")
    p.add_argument("--audio", default="copy",
                   help="'copy' per copiare l'audio (default) o un bitrate Opus, es. 160k")
    args = p.parse_args()

    controlla_ffmpeg()

    if args.input.is_dir():
        files = sorted(args.input.glob("*.mkv"))
        if not files:
            sys.exit("Nessun file .mkv trovato nella cartella.")
        out_dir = args.output or args.input / "compressi"
        out_dir.mkdir(parents=True, exist_ok=True)
        ok = sum(comprimi(f, out_dir / f.name, args) for f in files)
        print(f"\nCompletati {ok}/{len(files)} file in: {out_dir}")
    elif args.input.is_file():
        out = args.output or args.input.with_name(args.input.stem + "_compresso.mkv")
        if out.resolve() == args.input.resolve():
            sys.exit("L'output non può sovrascrivere il file di input.")
        comprimi(args.input, out, args)
    else:
        sys.exit(f"Percorso non trovato: {args.input}")


if __name__ == "__main__":
    main()
