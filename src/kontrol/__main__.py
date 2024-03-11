from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING

import pyk
from kevm_pyk.__main__ import ShowKCFGCommand, node_id_like
from kevm_pyk.cli import ExploreOptions, KEVMDisplayOptions, KOptions, KProveOptions
from kevm_pyk.cli import RPCOptions as KEVMRPCOptions
from kevm_pyk.utils import arg_pair_of
from pyk.cli.args import BugReportOptions, KompileOptions, LoggingOptions, ParallelOptions, SMTOptions
from pyk.cli.cli import CLI, Command
from pyk.cli.utils import file_path
from pyk.kbuild.utils import KVersion, k_version
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.proof.tui import APRProofViewer

from . import VERSION
from .cli import FoundryOptions, FoundryTestOptions, KGenOptions, KompileTargetOptions
from .foundry import (
    Foundry,
    foundry_get_model,
    foundry_list,
    foundry_merge_nodes,
    foundry_node_printer,
    foundry_refute_node,
    foundry_remove_node,
    foundry_section_edge,
    foundry_show,
    foundry_simplify_node,
    foundry_split_node,
    foundry_state_diff,
    foundry_step_node,
    foundry_to_dot,
    foundry_unrefute_node,
    read_deployment_state,
)
from .kompile import foundry_kompile
from .options import ProveOptions, RPCOptions
from .prove import foundry_prove
from .solc_to_k import solc_compile, solc_to_k

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Any, Final, TypeVar

    from pyk.cterm import CTerm
    from pyk.kcfg.kcfg import NodeIdLike
    from pyk.kcfg.tui import KCFGElem
    from pyk.utils import BugReport

    T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def list_of(elem_type: Callable[[str], T], delim: str = ';') -> Callable[[str], list[T]]:
    def parse(s: str) -> list[T]:
        return [elem_type(elem) for elem in s.split(delim)]

    return parse


def _parse_test_version_tuple(value: str) -> tuple[str, int | None]:
    if ':' in value:
        test, version = value.split(':')
        return (test, int(version))
    else:
        return (value, None)


def _ignore_arg(args: dict[str, Any], arg: str, cli_option: str) -> None:
    if arg in args:
        if args[arg] is not None:
            _LOGGER.warning(f'Ignoring command-line option: {cli_option}')
        args.pop(arg)


def _load_foundry(foundry_root: Path, bug_report: BugReport | None = None) -> Foundry:
    try:
        foundry = Foundry(foundry_root=foundry_root, bug_report=bug_report)
    except FileNotFoundError:
        print(
            f'File foundry.toml not found in: {str(foundry_root)!r}. Are you running kontrol in a Foundry project?',
            file=sys.stderr,
        )
        sys.exit(1)
    return foundry


def main() -> None:
    sys.setrecursionlimit(15000000)
    kontrol_cli = CLI(
        {
            VersionCommand,
            CompileCommand,
            SolcToKCommand,
            BuildCommand,
            LoadStateDiffCommand,
            ProveCommand,
            ShowCommand,
            ToDotCommand,
            SplitNodeCommand,
            ListCommand,
            ViewKCFGCommand,
            RemoveNodeCommand,
            RefuteNodeCommand,
            UnRefuteNodeCommand,
            SimplifyNodeCommand,
            StepNodeCommand,
            MergeNodesCommand,
            SectionEdgeCommand,
            GetModelCommand,
        }
    )

    _check_k_version()
    cmd = kontrol_cli.get_command()
    assert isinstance(cmd, LoggingOptions)
    logging.basicConfig(level=_loglevel(cmd), format=_LOG_FORMAT)
    cmd.exec()


def _check_k_version() -> None:
    expected_k_version = KVersion.parse(f'v{pyk.K_VERSION}')
    actual_k_version = k_version()

    if not _compare_versions(expected_k_version, actual_k_version):
        _LOGGER.warning(
            f'K version {expected_k_version.text} was expected but K version {actual_k_version.text} is being used.'
        )


def _compare_versions(ver1: KVersion, ver2: KVersion) -> bool:
    if ver1.major != ver2.major or ver1.minor != ver2.minor or ver1.patch != ver2.patch:
        return False

    if ver1.git == ver2.git:
        return True

    if ver1.git and ver2.git:
        return False

    git = ver1.git or ver2.git
    assert git  # git is not None for exactly one of ver1 and ver2
    return not git.ahead and not git.dirty


# Command implementation


class LoadStateDiffCommand(Command, FoundryOptions, LoggingOptions):
    contract_name: str
    accesses_file: Path
    contract_names: Path | None
    condense_state_diff: bool
    output_dir_name: str | None
    comment_generated_file: str
    license: str

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'contract_names': None,
            'condense_state_diff': False,
            'output_dir_name': None,
            'comment_generated_file': '// This file was autogenerated by running `kontrol load-state-diff`. Do not edit this file manually.\n',
            'license': 'UNLICENSED',
        }

    @staticmethod
    def name() -> str:
        return 'load-state-diff'

    @staticmethod
    def help_str() -> str:
        return 'Generate a state diff summary from an account access dict'

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('contract_name', type=str, help='Generated contract name')
        parser.add_argument('accesses_file', type=file_path, help='Path to accesses file')
        parser.add_argument(
            '--contract-names',
            dest='contract_names',
            type=file_path,
            help='Path to JSON containing deployment addresses and its respective contract names',
        )
        parser.add_argument(
            '--condense-state-diff',
            dest='condense_state_diff',
            type=bool,
            help='Deploy state diff as a single file',
        )
        parser.add_argument(
            '--output-dir',
            dest='output_dir_name',
            type=str,
            help='Path to write state diff .sol files, relative to foundry root',
        )
        parser.add_argument(
            '--comment-generated-files',
            dest='comment_generated_file',
            type=str,
            help='Comment to write at the top of the auto generated state diff files',
        )
        parser.add_argument(
            '--license',
            dest='license',
            type=str,
            help='License for the auto generated contracts',
        )

    def exec(self) -> None:
        foundry_state_diff(
            self.contract_name,
            self.accesses_file,
            contract_names=self.contract_names,
            output_dir_name=self.output_dir_name,
            foundry=_load_foundry(self.foundry_root),
            license=self.license,
            comment_generated_file=self.comment_generated_file,
            condense_state_diff=self.condense_state_diff,
        )


class VersionCommand(Command, LoggingOptions):
    @staticmethod
    def name() -> str:
        return 'version'

    @staticmethod
    def help_str() -> str:
        return 'Print out version of Kontrol command.'

    def exec(self) -> None:
        print(f'Kontrol version: {VERSION}')


class CompileCommand(Command, LoggingOptions):
    contract_file: Path

    @staticmethod
    def name() -> str:
        return 'compile'

    @staticmethod
    def help_str() -> str:
        return 'Generate combined JSON with solc compilation results.'

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('contract_file', type=file_path, help='Path to contract file.')

    def exec(self) -> None:
        res = solc_compile(self.contract_file)
        print(json.dumps(res))


class SolcToKCommand(Command, KOptions, KGenOptions, LoggingOptions):
    contract_file: Path
    contract_name: str

    @staticmethod
    def name() -> str:
        return 'solc-to-k'

    @staticmethod
    def help_str() -> str:
        return 'Output helper K definition for given JSON output from solc compiler.'

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('contract_file', type=file_path, help='Path to contract file.')
        parser.add_argument('contract_name', type=str, help='Name of contract to generate K helpers for.')

    def exec(self) -> None:
        k_text = solc_to_k(
            contract_file=self.contract_file,
            contract_name=self.contract_name,
            main_module=self.main_module,
            requires=self.requires,
            imports=self.imports,
        )
        print(k_text)


class BuildCommand(
    Command, KOptions, KGenOptions, KompileOptions, FoundryOptions, KompileTargetOptions, LoggingOptions
):
    regen: bool
    rekompile: bool
    no_forge_build: bool

    @staticmethod
    def name() -> str:
        return 'build'

    @staticmethod
    def help_str() -> str:
        return 'Kompile K definition corresponding to given output directory.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'regen': False,
            'rekompile': False,
            'no_forge_build': False,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--regen',
            dest='regen',
            default=None,
            action='store_true',
            help='Regenerate foundry.k even if it already exists.',
        )
        parser.add_argument(
            '--rekompile',
            dest='rekompile',
            default=None,
            action='store_true',
            help='Rekompile foundry.k even if kompiled definition already exists.',
        )
        parser.add_argument(
            '--no-forge-build',
            dest='no_forge_build',
            default=None,
            action='store_true',
            help="Do not call 'forge build' during kompilation.",
        )

    def exec(self) -> None:
        foundry_kompile(
            foundry=_load_foundry(self.foundry_root),
            includes=self.includes,
            regen=self.regen,
            rekompile=self.rekompile,
            requires=self.requires,
            imports=self.imports,
            ccopts=self.ccopts,
            llvm_kompile=self.llvm_kompile,
            debug=self.debug,
            verbose=self.verbose,
            target=self.target,
            no_forge_build=self.no_forge_build,
        )


class ProveCommand(
    Command,
    LoggingOptions,
    ParallelOptions,
    KOptions,
    KProveOptions,
    SMTOptions,
    KEVMRPCOptions,
    BugReportOptions,
    ExploreOptions,
    FoundryOptions,
):
    tests: list[tuple[str, int | None]]
    reinit: bool
    bmc_depth: int | None
    run_constructor: bool
    use_gas: bool
    break_on_cheatcodes: bool
    deployment_state_path: Path | None
    include_summaries: list[tuple[str, int | None]]
    with_non_general_state: bool
    xml_test_report: bool
    cse: bool

    @staticmethod
    def name() -> str:
        return 'prove'

    @staticmethod
    def help_str() -> str:
        return 'Run Foundry Proof.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'tests': [],
            'reinit': False,
            'bmc_depth': None,
            'run_constructor': False,
            'use_gas': False,
            'break_on_cheatcodes': False,
            'deployment_state_path': None,
            'include_summaries': [],
            'with_non_general_state': False,
            'xml_test_report': False,
            'cse': False,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--match-test',
            type=_parse_test_version_tuple,
            dest='tests',
            action='append',
            help=(
                'Specify contract function(s) to test using a regular expression. This will match functions'
                " based on their full signature,  e.g., 'ERC20Test.testTransfer(address,uint256)'. This option"
                ' can be used multiple times to add more functions to test.'
            ),
        )
        parser.add_argument(
            '--reinit',
            dest='reinit',
            default=None,
            action='store_true',
            help='Reinitialize CFGs even if they already exist.',
        )
        parser.add_argument(
            '--bmc-depth',
            dest='bmc_depth',
            type=int,
            help='Enables bounded model checking. Specifies the maximum depth to unroll all loops to.',
        )
        parser.add_argument(
            '--run-constructor',
            dest='run_constructor',
            default=None,
            action='store_true',
            help='Include the contract constructor in the test execution.',
        )
        parser.add_argument('--use-gas', dest='use_gas', default=None, action='store_true', help='Enables gas computation in KEVM.')
        parser.add_argument(
            '--break-on-cheatcodes',
            dest='break_on_cheatcodes',
            default=None,
            action='store_true',
            help='Break on all Foundry rules.',
        )
        parser.add_argument(
            '--init-node-from',
            dest='deployment_state_path',
            type=file_path,
            help='Path to JSON file containing the deployment state of the deployment process used for the project.',
        )
        parser.add_argument(
            '--include-summary',
            type=_parse_test_version_tuple,
            dest='include_summaries',
            action='append',
            help='Specify a summary to include as a lemma.',
        )
        parser.add_argument(
            '--with-non-general-state',
            dest='with_non_general_state',
            default=None,
            action='store_true',
            help='Flag used by Simbolik to initialise the state of a non test function as if it was a test function.',
        )
        parser.add_argument(
            '--xml-test-report',
            dest='xml_test_report',
            default=None,
            action='store_true',
            help='Generate a JUnit XML report',
        )
        parser.add_argument('--cse', dest='cse', default=None, action='store_true', help='Use Compositional Symbolic Execution')

    def exec(self) -> None:
        kore_rpc_command = (
            self.kore_rpc_command.split() if isinstance(self.kore_rpc_command, str) else self.kore_rpc_command
        )

        deployment_state_entries = (
            read_deployment_state(self.deployment_state_path) if self.deployment_state_path else None
        )

        prove_options = ProveOptions(
            auto_abstract_gas=self.auto_abstract_gas,
            reinit=self.reinit,
            bug_report=self.bug_report,
            bmc_depth=self.bmc_depth,
            max_depth=self.max_depth,
            break_every_step=self.break_every_step,
            break_on_jumpi=self.break_on_jumpi,
            break_on_calls=self.break_on_calls,
            break_on_storage=self.break_on_storage,
            break_on_basic_blocks=self.break_on_basic_blocks,
            break_on_cheatcodes=self.break_on_cheatcodes,
            workers=self.workers,
            counterexample_info=self.counterexample_info,
            max_iterations=self.max_iterations,
            run_constructor=self.run_constructor,
            fail_fast=self.fail_fast,
            use_gas=self.use_gas,
            deployment_state_entries=deployment_state_entries,
            active_symbolik=self.with_non_general_state,
            cse=self.cse,
        )

        rpc_options = RPCOptions(
            use_booster=self.use_booster,
            kore_rpc_command=kore_rpc_command,
            smt_timeout=self.smt_timeout,
            smt_retry_limit=self.smt_retry_limit,
            smt_tactic=self.smt_tactic,
            trace_rewrites=self.trace_rewrites,
            port=self.port,
            maude_port=self.maude_port,
        )

        results = foundry_prove(
            foundry=_load_foundry(self.foundry_root, self.bug_report),
            prove_options=prove_options,
            rpc_options=rpc_options,
            tests=self.tests,
            include_summaries=self.include_summaries,
            xml_test_report=self.xml_test_report,
        )
        failed = 0
        for proof in results:
            if proof.passed:
                print(f'PROOF PASSED: {proof.id}')
                print(f'time: {proof.formatted_exec_time()}s')
            else:
                failed += 1
                print(f'PROOF FAILED: {proof.id}')
                print(f'time: {proof.formatted_exec_time()}')
                failure_log = None
                if isinstance(proof, APRProof) and isinstance(proof.failure_info, APRFailureInfo):
                    failure_log = proof.failure_info
                if self.failure_info and failure_log is not None:
                    log = failure_log.print() + Foundry.help_info()
                    for line in log:
                        print(line)
        sys.exit(failed)


class ShowCommand(
    ShowKCFGCommand, FoundryTestOptions, KOptions, KEVMDisplayOptions, FoundryOptions, KEVMRPCOptions, LoggingOptions
):
    omit_unstable_output: bool
    to_kevm_claims: bool
    kevm_claim_dir: Path | None

    @staticmethod
    def name() -> str:
        return 'show'

    @staticmethod
    def help_str() -> str:
        return 'Print the CFG for a given proof.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'omit_unstable_output': False,
            'to_kevm_claims': False,
            'kevm_claim_dir': None,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--omit-unstable-output',
            dest='omit_unstable_output',
            default=None,
            action='store_true',
            help='Strip output that is likely to change without the contract logic changing',
        )
        parser.add_argument(
            '--to-kevm-claims',
            dest='to_kevm_claims',
            default=None,
            action='store_true',
            help='Generate a K module which can be run directly as KEVM claims for the given KCFG (best-effort).',
        )
        parser.add_argument(
            '--kevm-claim-dir',
            dest='kevm_claim_dir',
            help='Path to write KEVM claim files at.',
        )

    def exec(self) -> None:
        output = foundry_show(
            foundry=_load_foundry(self.foundry_root),
            test=self.test,
            version=self.version,
            nodes=self.nodes,
            node_deltas=self.node_deltas,
            to_module=self.to_module,
            to_kevm_claims=self.to_kevm_claims,
            kevm_claim_dir=self.kevm_claim_dir,
            minimize=self.minimize,
            omit_unstable_output=self.omit_unstable_output,
            sort_collections=self.sort_collections,
            pending=self.pending,
            failing=self.failing,
            failure_info=self.failure_info,
            counterexample_info=self.counterexample_info,
            port=self.port,
            maude_port=self.maude_port,
        )
        print(output)


class RefuteNodeCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    node: NodeIdLike

    @staticmethod
    def name() -> str:
        return 'refute-node'

    @staticmethod
    def help_str() -> str:
        return 'Refute a node and add its refutation as a subproof.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'omit_unstable_output': False,
            'to_kevm_claims': False,
            'kevm_claim_dir': None,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('node', type=node_id_like, help='Node to refute.')

    def exec(self) -> None:
        foundry_refute_node(
            foundry=_load_foundry(self.foundry_root), test=self.test, node=self.node, version=self.version
        )


class UnRefuteNodeCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    node: NodeIdLike

    @staticmethod
    def name() -> str:
        return 'unrefute-node'

    @staticmethod
    def help_str() -> str:
        return 'Disable refutation of a node and remove corresponding refutation subproof.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'omit_unstable_output': False,
            'to_kevm_claims': False,
            'kevm_claim_dir': None,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('node', type=node_id_like, help='Node to unrefute.')

    def exec(self) -> None:
        foundry_unrefute_node(
            foundry=_load_foundry(self.foundry_root), test=self.test, node=self.node, version=self.version
        )


class SplitNodeCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    node: NodeIdLike
    branch_condition: str

    @staticmethod
    def name() -> str:
        return 'split-node'

    @staticmethod
    def help_str() -> str:
        return 'Split a node on a given branch condition.'

    def exec(self) -> None:
        node_ids = foundry_split_node(
            foundry=_load_foundry(self.foundry_root),
            test=self.test,
            node=self.node,
            branch_condition=self.branch_condition,
            version=self.version,
        )

        print(f'Node {self.node} has been split into {node_ids} on condition {self.branch_condition}.')

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('node', type=node_id_like, help='Node to split.')
        parser.add_argument('branch_condition', type=str, help='Branch condition written in K.')


class ToDotCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    @staticmethod
    def name() -> str:
        return 'to-dot'

    @staticmethod
    def help_str() -> str:
        return 'Dump the given CFG for the test as DOT for visualization.'

    def exec(self) -> None:
        foundry_to_dot(foundry=_load_foundry(self.foundry_root), test=self.test, version=self.version)


class ListCommand(Command, KOptions, FoundryOptions, LoggingOptions):
    @staticmethod
    def name() -> str:
        return 'list'

    @staticmethod
    def help_str() -> str:
        return 'List information about CFGs on disk'

    def exec(self) -> None:
        stats = foundry_list(foundry=_load_foundry(self.foundry_root))
        print('\n'.join(stats))


class ViewKCFGCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    @staticmethod
    def name() -> str:
        return 'view-kcfg'

    @staticmethod
    def help_str() -> str:
        return 'Explore a given proof in the KCFG visualizer.'

    def exec(self) -> None:
        foundry = _load_foundry(self.foundry_root)
        test_id = foundry.get_test_id(self.test, self.version)
        contract_name, _ = test_id.split('.')
        proof = foundry.get_apr_proof(test_id)

        def _short_info(cterm: CTerm) -> Iterable[str]:
            return foundry.short_info_for_contract(contract_name, cterm)

        def _custom_view(elem: KCFGElem) -> Iterable[str]:
            return foundry.custom_view(contract_name, elem)

        node_printer = foundry_node_printer(foundry, contract_name, proof)
        viewer = APRProofViewer(proof, foundry.kevm, node_printer=node_printer, custom_view=_custom_view)
        viewer.run()


class RemoveNodeCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    node: NodeIdLike

    @staticmethod
    def name() -> str:
        return 'remove-node'

    @staticmethod
    def help_str() -> str:
        return 'Remove a node and its successors.'

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('node', type=node_id_like, help='Node to remove CFG subgraph from.')

    def exec(self) -> None:
        foundry_remove_node(
            foundry=_load_foundry(self.foundry_root), test=self.test, version=self.version, node=self.node
        )


class SimplifyNodeCommand(
    Command,
    FoundryTestOptions,
    SMTOptions,
    KEVMRPCOptions,
    BugReportOptions,
    KEVMDisplayOptions,
    FoundryOptions,
    LoggingOptions,
):
    node: NodeIdLike
    replace: bool

    @staticmethod
    def name() -> str:
        return 'simplify-node'

    @staticmethod
    def help_str() -> str:
        return 'Simplify a given node, and potentially replace it.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'replace': False,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('node', type=node_id_like, help='Node to simplify in CFG.')
        parser.add_argument('--replace', help='Replace the original node with the simplified variant in the graph.')

    def exec(self) -> None:
        kore_rpc_command = (
            self.kore_rpc_command.split() if isinstance(self.kore_rpc_command, str) else self.kore_rpc_command
        )

        rpc_options = RPCOptions(
            use_booster=self.use_booster,
            kore_rpc_command=kore_rpc_command,
            smt_timeout=self.smt_timeout,
            smt_retry_limit=self.smt_retry_limit,
            smt_tactic=self.smt_tactic,
            trace_rewrites=self.trace_rewrites,
            port=self.port,
            maude_port=self.maude_port,
        )

        pretty_term = foundry_simplify_node(
            foundry=_load_foundry(self.foundry_root, self.bug_report),
            test=self.test,
            version=self.version,
            node=self.node,
            rpc_options=rpc_options,
            replace=self.replace,
            minimize=self.minimize,
            sort_collections=self.sort_collections,
            bug_report=self.bug_report,
        )
        print(f'Simplified:\n{pretty_term}')


class StepNodeCommand(
    Command, FoundryTestOptions, KEVMRPCOptions, BugReportOptions, SMTOptions, FoundryOptions, LoggingOptions
):
    node: NodeIdLike
    repeat: int
    depth: int

    @staticmethod
    def name() -> str:
        return 'step-node'

    @staticmethod
    def help_str() -> str:
        return 'Step from a given node, adding it to the CFG.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'repeat': 1,
            'depth': 1,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('node', type=node_id_like, help='Node to step from in CFG.')
        parser.add_argument(
            '--repeat', type=int, help='How many node expansions to do from the given start node (>= 1).'
        )
        parser.add_argument('--depth', type=int, help='How many steps to take from initial node on edge.')

    def exec(self) -> None:
        kore_rpc_command = (
            self.kore_rpc_command.split() if isinstance(self.kore_rpc_command, str) else self.kore_rpc_command
        )

        rpc_options = RPCOptions(
            use_booster=self.use_booster,
            kore_rpc_command=kore_rpc_command,
            smt_timeout=self.smt_timeout,
            smt_retry_limit=self.smt_retry_limit,
            smt_tactic=self.smt_tactic,
            trace_rewrites=self.trace_rewrites,
            port=self.port,
            maude_port=self.maude_port,
        )

        foundry_step_node(
            foundry=_load_foundry(self.foundry_root, self.bug_report),
            test=self.test,
            version=self.version,
            node=self.node,
            rpc_options=rpc_options,
            repeat=self.repeat,
            depth=self.depth,
            bug_report=self.bug_report,
        )


class MergeNodesCommand(Command, FoundryTestOptions, FoundryOptions, LoggingOptions):
    nodes: list[NodeIdLike]

    @staticmethod
    def name() -> str:
        return 'merge-nodes'

    @staticmethod
    def help_str() -> str:
        return 'Merge multiple nodes into one branch.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'nodes': [],
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--node',
            type=node_id_like,
            dest='nodes',
            action='append',
            help='One node to be merged.',
        )

    def exec(self) -> None:
        foundry_merge_nodes(
            foundry=_load_foundry(self.foundry_root), node_ids=self.nodes, test=self.test, version=self.version
        )


class SectionEdgeCommand(
    Command, FoundryTestOptions, KEVMRPCOptions, BugReportOptions, SMTOptions, FoundryOptions, LoggingOptions
):
    edge: tuple[str, str]
    sections: int

    @staticmethod
    def name() -> str:
        return 'section-edge'

    @staticmethod
    def help_str() -> str:
        return 'Given an edge in the graph, cut it into sections to get intermediate nodes.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'sections': 2,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('edge', type=arg_pair_of(str, str), help='Edge to section in CFG.')
        parser.add_argument('--sections', type=int, help='Number of sections to make from edge (>= 2).')

    def exec(self) -> None:
        kore_rpc_command = (
            self.kore_rpc_command.split() if isinstance(self.kore_rpc_command, str) else self.kore_rpc_command
        )

        rpc_options = RPCOptions(
            use_booster=self.use_booster,
            kore_rpc_command=kore_rpc_command,
            smt_timeout=self.smt_timeout,
            smt_retry_limit=self.smt_retry_limit,
            smt_tactic=self.smt_tactic,
            trace_rewrites=self.trace_rewrites,
            port=self.port,
            maude_port=self.maude_port,
        )

        foundry_section_edge(
            foundry=_load_foundry(self.foundry_root, self.bug_report),
            test=self.test,
            version=self.version,
            rpc_options=rpc_options,
            edge=self.edge,
            sections=self.sections,
            bug_report=self.bug_report,
        )


class GetModelCommand(
    Command, FoundryTestOptions, KEVMRPCOptions, BugReportOptions, SMTOptions, FoundryOptions, LoggingOptions
):
    nodes: list[NodeIdLike]
    pending: bool
    failing: bool

    @staticmethod
    def name() -> str:
        return 'get-model'

    @staticmethod
    def help_str() -> str:
        return 'Display a model for a given node.'

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'nodes': [],
            'pending': False,
            'failing': False,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--node',
            type=node_id_like,
            dest='nodes',
            action='append',
            help='List of nodes to display the models of.',
        )
        parser.add_argument(
            '--pending', dest='pending', default=None, action='store_true', help='Also display models of pending nodes'
        )
        parser.add_argument(
            '--failing', dest='failing', default=None, action='store_true', help='Also display models of failing nodes'
        )

    def exec(self) -> None:
        kore_rpc_command = (
            self.kore_rpc_command.split() if isinstance(self.kore_rpc_command, str) else self.kore_rpc_command
        )

        rpc_options = RPCOptions(
            use_booster=self.use_booster,
            kore_rpc_command=kore_rpc_command,
            smt_timeout=self.smt_timeout,
            smt_retry_limit=self.smt_retry_limit,
            smt_tactic=self.smt_tactic,
            trace_rewrites=self.trace_rewrites,
            port=self.port,
            maude_port=self.maude_port,
        )
        output = foundry_get_model(
            foundry=_load_foundry(self.foundry_root),
            test=self.test,
            version=self.version,
            nodes=self.nodes,
            rpc_options=rpc_options,
            pending=self.pending,
            failing=self.failing,
            bug_report=self.bug_report,
        )
        print(output)


# Helpers


def _loglevel(args: LoggingOptions) -> int:
    if hasattr(args, 'debug') and args.debug:
        return logging.DEBUG

    if hasattr(args, 'verbose') and args.verbose:
        return logging.INFO

    return logging.WARNING


if __name__ == '__main__':
    main()
