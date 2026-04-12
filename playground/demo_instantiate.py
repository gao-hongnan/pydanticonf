"""End-to-end playground for pydanticonf.instantiate — run from project root.

Usage::

    python playground/demo_instantiate.py

Exercises every public feature of the instantiate subpackage:
  instantiate(), DynamicConfig[T], InstantiationError, BaseSettingsWithYaml.
"""

from __future__ import annotations

import functools
import sys
import time
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import SettingsConfigDict
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from playground.components import Decoder, Encoder, Pipeline, Tokenizer, TrainingLoop
from pydanticonf import BaseSettingsWithYaml, DynamicConfig, InstantiationError, instantiate

# ---------------------------------------------------------------------------
# Console & state
# ---------------------------------------------------------------------------

console = Console()
pass_count = 0
fail_count = 0
results: list[tuple[str, str, bool]] = []  # (section, label, passed)

TICK = 0.012  # seconds between row renders for the live effect


def check(section: str, label: str, condition: bool) -> None:
    global pass_count, fail_count  # noqa: PLW0603
    if condition:
        pass_count += 1
    else:
        fail_count += 1
    results.append((section, label, condition))


def show_config(title: str, cfg: dict[str, Any]) -> None:
    """Print a config dict as highlighted YAML-ish syntax."""
    import json

    text = json.dumps(cfg, indent=2)
    console.print(
        Panel(
            Syntax(text, "json", theme="monokai", line_numbers=False),
            title=f"[bold magenta]{title}[/]",
            border_style="magenta",
            expand=False,
        )
    )


def show_result(obj: object) -> None:
    """Print an instantiated object in a styled panel."""
    console.print(
        Panel(
            repr(obj),
            title="[bold green]result[/]",
            border_style="green",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# Target string constants
# ---------------------------------------------------------------------------

_ENC = "playground.components.Encoder"
_DEC = "playground.components.Decoder"
_TOK = "playground.components.Tokenizer"
_PIPE = "playground.components.Pipeline"
_LOOP = "playground.components.TrainingLoop"
_OPT_FN = "playground.components.create_optimizer"

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

SEC_1 = "1. Basic instantiation"
SEC_2 = "2. Recursive nesting"
SEC_3 = "3. _args_ positional"
SEC_4 = "4. _partial_ flag"
SEC_5 = "5. _recursive_=False"
SEC_6 = "6. **kwargs override"
SEC_7 = "7. *args replace"
SEC_8 = "8. DynamicConfig[T]"
SEC_9 = "9. Error handling"
SEC_10 = "10. YAML settings"
SEC_11 = "11. Deep nesting"
SEC_12 = "12. Passthrough"


# ========================== 1. Basic Instantiation =========================

enc = instantiate({"_target_": _ENC, "dim": 128, "num_layers": 2, "dropout": 0.05})
check(SEC_1, "type is Encoder", isinstance(enc, Encoder))
check(SEC_1, "dim == 128", enc.dim == 128)
check(SEC_1, "num_layers == 2", enc.num_layers == 2)
check(SEC_1, "dropout == 0.05", enc.dropout == 0.05)

# =================== 2. Recursive Nested Config ===========================

pipeline_cfg: dict[str, Any] = {
    "_target_": _PIPE,
    "encoder": {"_target_": _ENC, "dim": 512, "num_layers": 6, "dropout": 0.1},
    "decoder": {"_target_": _DEC, "dim": 512, "num_layers": 6},
    "tokenizer": {"_target_": _TOK, "vocab_size": 32000, "lowercase": True},
}
pipe = instantiate(pipeline_cfg)
check(SEC_2, "type is Pipeline", isinstance(pipe, Pipeline))
check(SEC_2, "encoder is Encoder", isinstance(pipe.encoder, Encoder))
check(SEC_2, "decoder is Decoder", isinstance(pipe.decoder, Decoder))
check(SEC_2, "tokenizer is Tokenizer", isinstance(pipe.tokenizer, Tokenizer))
check(SEC_2, "encoder.dim == 512", pipe.encoder.dim == 512)
check(SEC_2, "tokenizer.vocab_size == 32000", pipe.tokenizer.vocab_size == 32000)

# =================== 3. _args_ Positional Args ============================

opt_cfg: dict[str, Any] = {
    "_target_": _OPT_FN,
    "_args_": [0.001],
    "weight_decay": 0.01,
}
opt = instantiate(opt_cfg)
check(SEC_3, "returns dict", isinstance(opt, dict))
check(SEC_3, "lr == 0.001", opt["lr"] == 0.001)
check(SEC_3, "weight_decay == 0.01", opt["weight_decay"] == 0.01)

# =================== 4. _partial_ Flag ====================================

partial_enc = instantiate(
    {"_target_": _ENC, "dim": 768, "num_layers": 12},
    _partial_=True,
)
check(SEC_4, "returns functools.partial", isinstance(partial_enc, functools.partial))
check(SEC_4, "partial.func is Encoder", partial_enc.func is Encoder)
check(SEC_4, "partial.keywords has dim=768", partial_enc.keywords.get("dim") == 768)
realized = partial_enc(dropout=0.2)
check(SEC_4, "realized is Encoder", isinstance(realized, Encoder))
check(SEC_4, "realized.dim == 768", realized.dim == 768)
check(SEC_4, "realized.dropout == 0.2", realized.dropout == 0.2)

# =================== 5. _recursive_=False =================================

pipe_non_recursive = instantiate(
    {
        "_target_": _PIPE,
        "_recursive_": False,
        "encoder": {"_target_": _ENC, "dim": 256},
        "decoder": {"_target_": _DEC, "dim": 256},
        "tokenizer": None,
    },
)
check(SEC_5, "type is Pipeline", isinstance(pipe_non_recursive, Pipeline))
check(SEC_5, "encoder is dict (not Encoder)", isinstance(pipe_non_recursive.encoder, dict))
check(SEC_5, "decoder is dict (not Decoder)", isinstance(pipe_non_recursive.decoder, dict))
check(
    SEC_5,
    "encoder dict has _target_",
    pipe_non_recursive.encoder.get("_target_") == _ENC,
)

# =================== 6. Call-time **kwargs Override ========================

base_cfg: dict[str, Any] = {"_target_": _ENC, "dim": 256, "num_layers": 4, "dropout": 0.1}
overridden = instantiate(base_cfg, dim=1024, num_layers=24)
check(SEC_6, "type is Encoder", isinstance(overridden, Encoder))
check(SEC_6, "dim overridden to 1024", overridden.dim == 1024)
check(SEC_6, "num_layers overridden to 24", overridden.num_layers == 24)
check(SEC_6, "dropout kept from config (0.1)", overridden.dropout == 0.1)

# =================== 7. Call-time *args Replace ============================

opt_replaced = instantiate(
    {"_target_": _OPT_FN, "_args_": [0.001], "weight_decay": 0.01},
    0.1,
)
check(SEC_7, "lr replaced to 0.1", opt_replaced["lr"] == 0.1)
check(SEC_7, "weight_decay kept", opt_replaced["weight_decay"] == 0.01)

# =================== 8. DynamicConfig[T] ==================================


class EncoderConfig(DynamicConfig[Encoder]):
    pass


cfg_obj = EncoderConfig.model_validate({"dim": 384, "num_layers": 8, "dropout": 0.15})
expected_target = f"{Encoder.__module__}.{Encoder.__qualname__}"
check(SEC_8, "auto-injected _target_", cfg_obj.target_ == expected_target)
enc_from_dc = instantiate(cfg_obj)
check(SEC_8, "instantiate -> Encoder", isinstance(enc_from_dc, Encoder))
check(SEC_8, "dim == 384", enc_from_dc.dim == 384)
check(SEC_8, "num_layers == 8", enc_from_dc.num_layers == 8)

cfg_explicit = EncoderConfig.model_validate({"_target_": _DEC, "dim": 64, "num_layers": 2})
check(SEC_8, "explicit _target_ preserved", cfg_explicit.target_ == _DEC)
dec_from_dc = instantiate(cfg_explicit)
check(SEC_8, "produces Decoder", isinstance(dec_from_dc, Decoder))

# =================== 9. Error Handling =====================================

try:
    instantiate({"_target_": "nonexistent.module.BadClass", "x": 1})
    check(SEC_9, "should have raised", False)
except InstantiationError as e:
    check(SEC_9, "caught InstantiationError", True)
    check(SEC_9, "target preserved", e.target == "nonexistent.module.BadClass")
    check(SEC_9, "has __cause__", e.__cause__ is not None)

try:
    instantiate(
        {
            "_target_": _PIPE,
            "encoder": {"_target_": _ENC, "bad_kwarg": 999},
            "decoder": {"_target_": _DEC, "dim": 64},
            "tokenizer": None,
        }
    )
    check(SEC_9, "should have raised for bad kwarg", False)
except InstantiationError as e:
    check(SEC_9, "caught nested error", True)
    check(SEC_9, "full_key is 'encoder'", e.full_key == "encoder")
    check(SEC_9, "cause is TypeError", isinstance(e.__cause__, TypeError))

# =================== 10. BaseSettingsWithYaml ==============================

yaml_path = Path(__file__).parent / "config.yaml"


class DemoSettings(BaseSettingsWithYaml):
    app_name: str = "default"
    debug: bool = False
    pipeline: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        yaml_file=str(yaml_path),
        yaml_file_encoding="utf-8",
    )


settings = DemoSettings()
check(SEC_10, "app_name from YAML", settings.app_name == "pydanticonf-demo")
check(SEC_10, "debug from YAML", settings.debug is True)
check(SEC_10, "pipeline has _target_", "_target_" in settings.pipeline)
pipe_from_yaml = instantiate(settings.pipeline)
check(SEC_10, "Pipeline from YAML", isinstance(pipe_from_yaml, Pipeline))
check(SEC_10, "encoder.dim == 512", pipe_from_yaml.encoder.dim == 512)
check(SEC_10, "tokenizer.lowercase", pipe_from_yaml.tokenizer.lowercase is True)

# =================== 11. Deep Nesting =====================================

deep_cfg: dict[str, Any] = {
    "_target_": _LOOP,
    "epochs": 50,
    "optimizer": {
        "_target_": _OPT_FN,
        "_args_": [0.0003],
        "weight_decay": 0.05,
    },
    "pipeline": {
        "_target_": _PIPE,
        "encoder": {"_target_": _ENC, "dim": 1024, "num_layers": 24, "dropout": 0.1},
        "decoder": {"_target_": _DEC, "dim": 1024, "num_layers": 24},
        "tokenizer": {"_target_": _TOK, "vocab_size": 50000, "lowercase": False},
    },
}
loop = instantiate(deep_cfg)
check(SEC_11, "type is TrainingLoop", isinstance(loop, TrainingLoop))
check(SEC_11, "epochs == 50", loop.epochs == 50)
check(SEC_11, "optimizer is dict", isinstance(loop.optimizer, dict))
check(SEC_11, "optimizer lr == 0.0003", loop.optimizer["lr"] == 0.0003)
check(SEC_11, "pipeline is Pipeline", isinstance(loop.pipeline, Pipeline))
check(SEC_11, "encoder is Encoder", isinstance(loop.pipeline.encoder, Encoder))
check(SEC_11, "encoder.dim == 1024", loop.pipeline.encoder.dim == 1024)
check(SEC_11, "decoder.num_layers == 24", loop.pipeline.decoder.num_layers == 24)
check(SEC_11, "tokenizer.vocab_size == 50000", loop.pipeline.tokenizer.vocab_size == 50000)

# =================== 12. Passthrough (no _target_) ========================

plain = instantiate({"a": 1, "b": {"c": 2}})
check(SEC_12, "plain dict returned", plain == {"a": 1, "b": {"c": 2}})
mixed_list = instantiate([1, {"_target_": _ENC, "dim": 64}, "hello"])
check(SEC_12, "list[0] is int", mixed_list[0] == 1)
check(SEC_12, "list[1] is Encoder", isinstance(mixed_list[1], Encoder))
check(SEC_12, "list[2] is str", mixed_list[2] == "hello")
check(SEC_12, "scalar int passthrough", instantiate(42) == 42)
check(SEC_12, "scalar None passthrough", instantiate(None) is None)


# ===========================================================================
# Live render
# ===========================================================================


def main() -> None:
    console.print()

    # Show an example config panel
    show_config("deep nesting config (section 11)", deep_cfg)
    console.print()

    # Animate the results table row by row
    with Live(build_partial_table(0), console=console, refresh_per_second=30) as live:
        for n in range(1, len(results) + 1):
            time.sleep(TICK)
            live.update(build_partial_table(n))

    console.print()

    # Show one featured result object
    show_result(loop)

    # Summary banner
    if fail_count == 0:
        console.print(
            Panel(
                f"[bold green]{pass_count} passed[/], [dim]{fail_count} failed[/]",
                title="[bold cyan]ALL CHECKS PASSED[/]",
                border_style="green",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                f"[green]{pass_count} passed[/], [bold red]{fail_count} failed[/]",
                title="[bold red]SOME CHECKS FAILED[/]",
                border_style="red",
                expand=False,
            )
        )


def build_partial_table(n: int) -> Table:
    """Build a table showing only the first *n* results (for animation)."""
    table = Table(
        title="pydanticonf.instantiate  --  feature demo",
        title_style="bold cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Section", style="bold white", width=22, no_wrap=True)
    table.add_column("Check", no_wrap=True, min_width=30)
    table.add_column("", justify="center", width=6)

    prev_section = ""
    for i, (sec, label, passed) in enumerate(results[:n], 1):
        status = Text("PASS", style="bold green") if passed else Text("FAIL", style="bold red")
        show_sec = sec if sec != prev_section else ""
        prev_section = sec
        table.add_row(str(i), show_sec, label, status)

    return table


if __name__ == "__main__":
    main()
    sys.exit(1 if fail_count > 0 else 0)
