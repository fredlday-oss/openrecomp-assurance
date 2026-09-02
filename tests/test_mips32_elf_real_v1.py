import pytest

from harness.runner.openrecomp_mips32_elf import (
    MIPS32ELFAssuranceError,
    SEEDS,
    assembly_for,
    canonical_records,
    mutate_records,
)

SAMPLE = """\
00001000 24081234
00001004 340900f0
00001008 03e00008
0000100c 00000000
"""


def test_canonical_records_are_contiguous():
    records = canonical_records(SAMPLE)
    assert records == (
        (0x1000, 0x24081234),
        (0x1004, 0x340900F0),
        (0x1008, 0x03E00008),
        (0x100C, 0x00000000),
    )


def test_canonical_records_reject_hole():
    with pytest.raises(MIPS32ELFAssuranceError, match="not contiguous"):
        canonical_records("00001000 24081234\n00001008 03e00008\n")


def test_seed_mutation_changes_exactly_one_word():
    records = canonical_records(SAMPLE)
    changed = mutate_records(records, 0x340900F0, 0x340900F1)
    assert sum(a != b for a, b in zip(records, changed)) == 1
    assert changed[1] == (0x1004, 0x340900F1)


def test_all_declared_seeds_are_unique():
    assert len(SEEDS) == 5
    assert len({seed_id for seed_id, *_ in SEEDS}) == 5
    assert len({old for _, old, _, _ in SEEDS}) == 5


def test_assembly_preserves_word_order_and_function_size():
    assembly = assembly_for(canonical_records(SAMPLE))
    assert assembly.index(".word 0x24081234") < assembly.index(".word 0x340900f0")
    assert ".globl logic_shift_main" in assembly
    assert ".type logic_shift_main, @function" in assembly
    assert ".size logic_shift_main, .-logic_shift_main" in assembly
