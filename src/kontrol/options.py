from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyk.utils import BugReport

    from .deployment import SummaryEntry


@dataclass(frozen=True)
class ProveOptions:
    auto_abstract_gas: bool
    bug_report: BugReport | None
    bmc_depth: int | None
    max_depth: int
    break_every_step: bool
    break_on_jumpi: bool
    break_on_calls: bool
    break_on_storage: bool
    break_on_basic_blocks: bool
    break_on_cheatcodes: bool
    workers: int
    counterexample_info: bool
    max_iterations: int | None
    run_constructor: bool
    fail_fast: bool
    reinit: bool
    use_gas: bool
    failure_info: bool
    summary_entries: Iterable[SummaryEntry] | None
    fast_check_subsumption: bool | None

    def __init__(
        self,
        *,
        auto_abstract_gas: bool | None = None,
        bug_report: BugReport | None = None,
        bmc_depth: int | None = None,
        max_depth: int = 1000,
        break_every_step: bool | None = None,
        break_on_jumpi: bool | None = None,
        break_on_calls: bool | None = None,
        break_on_storage: bool | None = None,
        break_on_basic_blocks: bool | None = None,
        break_on_cheatcodes: bool | None = None,
        workers: int = 1,
        counterexample_info: bool | None = None,
        max_iterations: int | None = None,
        run_constructor: bool | None = None,
        fail_fast: bool | None = None,
        reinit: bool | None = None,
        use_gas: bool | None = None,
        failure_info: bool | None = None,
        summary_entries: list[SummaryEntry] | None = None,
        fast_check_subsumption: bool | None = None,
    ) -> None:
        object.__setattr__(self, 'auto_abstract_gas', bool(auto_abstract_gas))
        object.__setattr__(self, 'bug_report', bug_report)
        object.__setattr__(self, 'bmc_depth', bmc_depth)
        object.__setattr__(self, 'max_depth', max_depth)
        object.__setattr__(self, 'break_every_step', bool(break_every_step))
        object.__setattr__(self, 'break_on_jumpi', bool(break_on_jumpi))
        object.__setattr__(self, 'break_on_calls', bool(break_on_calls))
        object.__setattr__(self, 'break_on_storage', bool(break_on_storage))
        object.__setattr__(self, 'break_on_basic_blocks', bool(break_on_basic_blocks))
        object.__setattr__(self, 'break_on_cheatcodes', bool(break_on_cheatcodes))
        object.__setattr__(self, 'workers', workers)
        object.__setattr__(self, 'counterexample_info', True if counterexample_info is None else counterexample_info)
        object.__setattr__(self, 'max_iterations', max_iterations)
        object.__setattr__(self, 'run_constructor', bool(run_constructor))
        object.__setattr__(self, 'fail_fast', True if fail_fast is None else fail_fast)
        object.__setattr__(self, 'reinit', bool(reinit))
        object.__setattr__(self, 'use_gas', bool(use_gas))
        object.__setattr__(self, 'failure_info', True if failure_info is None else failure_info)
        object.__setattr__(self, 'summary_entries', summary_entries)
        object.__setattr__(
            self, 'fast_check_subsumption', True if fast_check_subsumption is None else fast_check_subsumption
        )


@dataclass(frozen=True)
class RPCOptions:
    use_booster: bool
    kore_rpc_command: tuple[str, ...]
    smt_timeout: int | None
    smt_retry_limit: int | None
    smt_tactic: str | None
    trace_rewrites: bool
    port: int | None
    maude_port: int | None

    def __init__(
        self,
        *,
        use_booster: bool | None = None,
        kore_rpc_command: str | Iterable[str] | None = None,
        smt_timeout: int | None = None,
        smt_retry_limit: int | None = None,
        smt_tactic: str | None = None,
        trace_rewrites: bool | None = None,
        port: int | None = None,
        maude_port: int | None = None,
    ) -> None:
        if kore_rpc_command is None:
            kore_rpc_command = (
                ('kore-rpc-booster',) if (True if use_booster is None else use_booster) else ('kore-rpc',)
            )
        elif isinstance(kore_rpc_command, str):
            kore_rpc_command = (kore_rpc_command,)
        else:
            kore_rpc_command = tuple(kore_rpc_command)
        object.__setattr__(self, 'use_booster', True if use_booster is None else use_booster)
        object.__setattr__(self, 'kore_rpc_command', kore_rpc_command)
        object.__setattr__(self, 'smt_timeout', smt_timeout)
        object.__setattr__(self, 'smt_retry_limit', smt_retry_limit)
        object.__setattr__(self, 'smt_tactic', smt_tactic)
        object.__setattr__(self, 'trace_rewrites', bool(trace_rewrites))
        object.__setattr__(self, 'port', port)
        object.__setattr__(self, 'maude_port', maude_port)
