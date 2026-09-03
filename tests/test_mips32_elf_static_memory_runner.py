from harness.runner.openrecomp_mips32_elf_static_memory import (
    BASE_BSS_ADDR,
    BASE_RECORDS,
    OBSERVE_ADDR,
    OBSERVE_SIZE,
    SEEDS,
    StaticVariantSpec,
    assembly_for,
    linker_script_for,
)


def test_seed_set_is_exactly_five_and_unique():
    assert len(SEEDS) == 5
    assert len({seed.fixture_id for seed in SEEDS}) == 5


def test_baseline_contains_real_static_load_store_path():
    assert 0x8D090000 in BASE_RECORDS  # lw from .rodata base
    assert 0x8D4B0000 in BASE_RECORDS  # lw from .data base
    assert 0xAD4C0000 in BASE_RECORDS  # sw to .data
    assert 0x8DAE0000 in BASE_RECORDS  # lw from .bss
    assert 0xADA20000 in BASE_RECORDS  # sw to .bss


def test_bss_layout_seed_moves_loader_and_guest_address_together():
    seed = next(item for item in SEEDS if item.fixture_id == "seed-bss-layout-move")
    assert seed.bss_addr == 0x3020
    assert 0x240D3020 in seed.records
    assert 0x240D3010 not in seed.records


def test_observable_window_covers_baseline_and_moved_bss():
    end = OBSERVE_ADDR + OBSERVE_SIZE
    assert OBSERVE_ADDR <= BASE_BSS_ADDR and BASE_BSS_ADDR + 4 <= end
    assert OBSERVE_ADDR <= 0x3020 and 0x3020 + 4 <= end


def test_generated_sources_keep_static_sections_explicit():
    spec = StaticVariantSpec("test")
    assembly = assembly_for(spec)
    linker = linker_script_for(spec)
    assert ".openrecomp_rodata" in assembly
    assert ".openrecomp_data" in assembly
    assert ".openrecomp_bss" in assembly
    assert ".rodata" in linker and ".data" in linker and ".bss" in linker
    assert "0x00003010" in linker
