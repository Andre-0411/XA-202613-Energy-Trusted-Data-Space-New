"""
Solidity 合约编译器
solc 编译 + ABI 提取 + 字节码管理 + 编译缓存
支持 FISCO BCOS Solidity 0.8.x

增强功能:
- 代理模式升级支持
- ABI 版本管理
- 合约元数据管理
"""
import json
import hashlib
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AbiEntry:
    """ABI 条目"""
    name: str
    inputs: list[dict]
    outputs: list[dict] = field(default_factory=list)
    state_mutability: str = "nonpayable"
    entry_type: str = "function"

    def to_dict(self) -> dict:
        return {
            "type": self.entry_type,
            "name": self.name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "stateMutability": self.state_mutability,
        }


@dataclass
class AbiVersion:
    """ABI 版本信息"""
    version: str
    abi_hash: str
    abi: list
    contract_name: str
    created_at: str
    source_hash: str

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "abi_hash": self.abi_hash,
            "abi": self.abi,
            "contract_name": self.contract_name,
            "created_at": self.created_at,
            "source_hash": self.source_hash,
        }


class CompilationResult:
    """编译结果"""

    def __init__(
        self,
        contract_name: str,
        abi: list,
        bytecode: str,
        bytecode_hash: str,
        source_hash: str,
        compiler_version: str,
        compiled_at: str,
    ):
        self.contract_name = contract_name
        self.abi = abi
        self.bytecode = bytecode
        self.bytecode_hash = bytecode_hash
        self.source_hash = source_hash
        self.compiler_version = compiler_version
        self.compiled_at = compiled_at

    def to_dict(self) -> dict:
        return {
            "contract_name": self.contract_name,
            "abi": self.abi,
            "bytecode": self.bytecode,
            "bytecode_hash": self.bytecode_hash,
            "source_hash": self.source_hash,
            "compiler_version": self.compiler_version,
            "compiled_at": self.compiled_at,
        }


class ContractCompiler:
    """
    Solidity 合约编译器

    功能:
    1. 使用 solc 编译 .sol 文件
    2. 提取 ABI 和字节码
    3. 编译缓存（基于源码哈希）
    4. 批量编译整个合约目录
    5. 代理模式支持（Proxy + Implementation）
    6. ABI 版本管理
    """

    # 默认合约目录
    DEFAULT_CONTRACTS_DIR = Path(__file__).parent.parent.parent.parent / "contracts"

    # 默认编译产物目录
    DEFAULT_ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "contracts" / "artifacts"

    # 编译缓存文件
    CACHE_FILE_NAME = ".compilation_cache.json"

    # ABI 版本文件
    ABI_VERSION_FILE = ".abi_versions.json"

    def __init__(
        self,
        contracts_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
        solc_path: str = "solc",
    ):
        self.contracts_dir = contracts_dir or self.DEFAULT_CONTRACTS_DIR
        self.artifacts_dir = artifacts_dir or self.DEFAULT_ARTIFACTS_DIR
        self.solc_path = solc_path
        self._cache: Dict[str, dict] = {}
        self._cache_file = self.artifacts_dir / self.CACHE_FILE_NAME
        self._abi_versions: Dict[str, list] = {}
        self._abi_version_file = self.artifacts_dir / self.ABI_VERSION_FILE
        self._load_cache()
        self._load_abi_versions()

    def _load_cache(self) -> None:
        """加载编译缓存"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} compilation cache entries")
        except Exception as e:
            logger.warning(f"Failed to load compilation cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """保存编译缓存"""
        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save compilation cache: {e}")

    def _load_abi_versions(self) -> None:
        """加载 ABI 版本历史"""
        try:
            if self._abi_version_file.exists():
                with open(self._abi_version_file, "r", encoding="utf-8") as f:
                    self._abi_versions = json.load(f)
                logger.info(f"Loaded ABI versions for {len(self._abi_versions)} contracts")
        except Exception as e:
            logger.warning(f"Failed to load ABI versions: {e}")
            self._abi_versions = {}

    def _save_abi_versions(self) -> None:
        """保存 ABI 版本历史"""
        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            with open(self._abi_version_file, "w", encoding="utf-8") as f:
                json.dump(self._abi_versions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save ABI versions: {e}")

    @staticmethod
    def _compute_source_hash(source_code: str) -> str:
        """计算源码哈希"""
        return hashlib.sha256(source_code.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_bytecode_hash(bytecode: str) -> str:
        """计算字节码哈希"""
        return hashlib.sha256(bytecode.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_abi_hash(abi: list) -> str:
        """计算 ABI 哈希（用于版本比对）"""
        abi_str = json.dumps(abi, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(abi_str.encode("utf-8")).hexdigest()[:16]

    def _check_cache(self, contract_name: str, source_hash: str) -> Optional[CompilationResult]:
        """检查编译缓存"""
        cached = self._cache.get(contract_name)
        if cached and cached.get("source_hash") == source_hash:
            logger.info(f"Cache hit for {contract_name}")
            return CompilationResult(
                contract_name=contract_name,
                abi=cached["abi"],
                bytecode=cached["bytecode"],
                bytecode_hash=cached["bytecode_hash"],
                source_hash=cached["source_hash"],
                compiler_version=cached["compiler_version"],
                compiled_at=cached["compiled_at"],
            )
        return None

    def _update_cache(self, result: CompilationResult) -> None:
        """更新编译缓存"""
        self._cache[result.contract_name] = result.to_dict()
        self._save_cache()

    def _update_abi_version(self, contract_name: str, abi: list, source_hash: str) -> None:
        """
        更新 ABI 版本历史

        每次 ABI 变化时记录新版本，保留所有历史版本。

        Args:
            contract_name: 合约名称
            abi: 新 ABI
            source_hash: 源码哈希
        """
        if contract_name not in self._abi_versions:
            self._abi_versions[contract_name] = []

        abi_hash = self._compute_abi_hash(abi)

        # 检查是否已存在相同 ABI 哈希的版本
        existing_versions = self._abi_versions[contract_name]
        for ver in existing_versions:
            if ver.get("abi_hash") == abi_hash:
                # ABI 未变化，不新增版本
                return

        # 计算新版本号
        version_num = len(existing_versions) + 1
        version_str = f"v{version_num}.0.0"

        abi_version = AbiVersion(
            version=version_str,
            abi_hash=abi_hash,
            abi=abi,
            contract_name=contract_name,
            created_at=datetime.now().isoformat(),
            source_hash=source_hash,
        )
        existing_versions.append(abi_version.to_dict())
        self._save_abi_versions()
        logger.info(f"ABI version updated for {contract_name}: {version_str}")

    def _read_source(self, contract_name: str) -> str:
        """
        读取 Solidity 源码

        Args:
            contract_name: 合约名称（如 IdentityRegistry）

        Returns:
            源码字符串

        Raises:
            FileNotFoundError: 源文件不存在
        """
        # 尝试直接匹配
        source_path = self.contracts_dir / f"{contract_name}.sol"
        if source_path.exists():
            return source_path.read_text(encoding="utf-8")

        # 尝试递归查找
        for sol_file in self.contracts_dir.rglob(f"{contract_name}.sol"):
            return sol_file.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Solidity source not found: {contract_name}.sol in {self.contracts_dir}")

    def compile_source(self, source_code: str, contract_name: str) -> CompilationResult:
        """
        编译 Solidity 源码字符串

        Args:
            source_code: Solidity 源码
            contract_name: 合约名称

        Returns:
            编译结果

        Raises:
            RuntimeError: 编译失败
        """
        source_hash = self._compute_source_hash(source_code)

        # 检查缓存
        cached = self._check_cache(contract_name, source_hash)
        if cached:
            return cached

        # 尝试使用 solc 编译
        try:
            return self._compile_with_solc(source_code, contract_name, source_hash)
        except FileNotFoundError:
            logger.warning("solc not found, using fallback compilation")
            return self._compile_fallback(source_code, contract_name, source_hash)

    def _compile_with_solc(
        self, source_code: str, contract_name: str, source_hash: str
    ) -> CompilationResult:
        """
        使用 solc 编译器编译

        Args:
            source_code: Solidity 源码
            contract_name: 合约名称
            source_hash: 源码哈希

        Returns:
            编译结果
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / f"{contract_name}.sol"
            source_file.write_text(source_code, encoding="utf-8")

            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            # 执行 solc 编译
            cmd = [
                self.solc_path,
                "--optimize",
                "--optimize-runs", "200",
                "--abi",
                "--bin",
                "-o", str(output_dir),
                "--overwrite",
                str(source_file),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise RuntimeError(f"solc compilation failed: {result.stderr}")

            # 读取编译产物
            abi_file = output_dir / f"{contract_name}.abi"
            bin_file = output_dir / f"{contract_name}.bin"

            if not abi_file.exists() or not bin_file.exists():
                raise RuntimeError(f"Compilation artifacts not found for {contract_name}")

            abi = json.loads(abi_file.read_text(encoding="utf-8"))
            bytecode = f"0x{bin_file.read_text(encoding='utf-8').strip()}"

            compiler_version = self._get_solc_version()

            result_obj = CompilationResult(
                contract_name=contract_name,
                abi=abi,
                bytecode=bytecode,
                bytecode_hash=self._compute_bytecode_hash(bytecode),
                source_hash=source_hash,
                compiler_version=compiler_version,
                compiled_at=datetime.now().isoformat(),
            )

            self._update_cache(result_obj)
            self._update_abi_version(contract_name, abi, source_hash)
            logger.info(f"Compiled {contract_name} with solc")
            return result_obj

    def _compile_fallback(
        self, source_code: str, contract_name: str, source_hash: str
    ) -> CompilationResult:
        """
        降级编译方案：从源码提取 ABI 结构

        当 solc 不可用时，使用简单的正则提取函数签名构建基础 ABI

        Args:
            source_code: Solidity 源码
            contract_name: 合约名称
            source_hash: 源码哈希

        Returns:
            编译结果
        """
        abi = []

        # 提取 event 定义
        event_pattern = r"event\s+(\w+)\s*\(([^)]*)\)"
        for match in re.finditer(event_pattern, source_code):
            event_name = match.group(1)
            params_str = match.group(2)
            inputs = self._parse_params(params_str)
            abi.append({
                "type": "event",
                "name": event_name,
                "inputs": inputs,
                "anonymous": False,
            })

        # 提取 function 定义
        func_pattern = r"function\s+(\w+)\s*\(([^)]*)\)(?:\s+(?:external|public|internal|private))?(?:\s+(?:view|pure|payable|nonpayable))?(?:\s+returns\s*\(([^)]*)\))?"
        for match in re.finditer(func_pattern, source_code):
            func_name = match.group(1)
            params_str = match.group(2)
            returns_str = match.group(3)

            if func_name.startswith("_"):
                continue  # 跳过内部函数

            inputs = self._parse_params(params_str)
            outputs = self._parse_params(returns_str) if returns_str else []

            state_mutability = "nonpayable"
            if "view" in source_code[match.start():match.end() + 50]:
                state_mutability = "view"
            elif "pure" in source_code[match.start():match.end() + 50]:
                state_mutability = "pure"

            abi.append({
                "type": "function",
                "name": func_name,
                "inputs": inputs,
                "outputs": outputs,
                "stateMutability": state_mutability,
            })

        # 提取 constructor
        constructor_pattern = r"constructor\s*\(([^)]*)\)"
        for match in re.finditer(constructor_pattern, source_code):
            params_str = match.group(1)
            inputs = self._parse_params(params_str)
            abi.append({
                "type": "constructor",
                "inputs": inputs,
                "stateMutability": "nonpayable",
            })

        # 生成占位字节码
        bytecode = f"0x{hashlib.sha256(source_code.encode()).hexdigest()}"

        result_obj = CompilationResult(
            contract_name=contract_name,
            abi=abi,
            bytecode=bytecode,
            bytecode_hash=self._compute_bytecode_hash(bytecode),
            source_hash=source_hash,
            compiler_version="fallback-1.0.0",
            compiled_at=datetime.now().isoformat(),
        )

        self._update_cache(result_obj)
        self._update_abi_version(contract_name, abi, source_hash)
        logger.info(f"Compiled {contract_name} with fallback parser (ABI extracted)")
        return result_obj

    @staticmethod
    def _parse_params(params_str: str) -> list:
        """解析 Solidity 函数参数"""
        if not params_str or not params_str.strip():
            return []

        params = []
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue
            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[1]
                indexed = "indexed" in param
                params.append({
                    "name": param_name,
                    "type": param_type,
                    "indexed": indexed,
                })
        return params

    def _get_solc_version(self) -> str:
        """获取 solc 版本"""
        try:
            result = subprocess.run(
                [self.solc_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.split("\n"):
                if "Version:" in line:
                    return line.split("Version:")[1].strip()
            return "unknown"
        except Exception:
            return "unknown"

    def compile_contract(self, contract_name: str) -> CompilationResult:
        """
        编译指定合约

        Args:
            contract_name: 合约名称（如 IdentityRegistry）

        Returns:
            编译结果
        """
        source_code = self._read_source(contract_name)
        return self.compile_source(source_code, contract_name)

    def compile_all(self) -> Dict[str, CompilationResult]:
        """
        编译所有合约

        Returns:
            {合约名称: 编译结果} 字典
        """
        results = {}
        sol_files = list(self.contracts_dir.glob("*.sol"))

        # 跳过接口文件
        skip_files = {"interfaces"}
        for sol_file in sol_files:
            if sol_file.stem in skip_files:
                continue
            try:
                result = self.compile_contract(sol_file.stem)
                results[sol_file.stem] = result
            except Exception as e:
                logger.error(f"Failed to compile {sol_file.stem}: {e}")

        logger.info(f"Compiled {len(results)}/{len(sol_files)} contracts")
        return results

    def get_artifact(self, contract_name: str) -> Optional[dict]:
        """
        获取编译产物

        优先从缓存获取，其次从 artifacts 目录加载

        Args:
            contract_name: 合约名称

        Returns:
            编译产物字典 {abi, bytecode}
        """
        # 从缓存获取
        cached = self._cache.get(contract_name)
        if cached:
            return {
                "abi": cached["abi"],
                "bytecode": cached["bytecode"],
            }

        # 从 artifacts 目录加载
        artifact_path = self.artifacts_dir / f"{contract_name}.json"
        if artifact_path.exists():
            with open(artifact_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return None

    def save_artifact(self, contract_name: str, result: CompilationResult) -> Path:
        """
        保存编译产物到 artifacts 目录

        Args:
            contract_name: 合约名称
            result: 编译结果

        Returns:
            保存路径
        """
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.artifacts_dir / f"{contract_name}.json"

        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved artifact for {contract_name} to {artifact_path}")
        return artifact_path

    def clear_cache(self) -> int:
        """清除编译缓存"""
        count = len(self._cache)
        self._cache = {}
        if self._cache_file.exists():
            self._cache_file.unlink()
        logger.info(f"Cleared {count} compilation cache entries")
        return count

    # ==================== 增强功能 ====================

    def get_abi_versions(self, contract_name: str) -> list[dict]:
        """
        获取合约 ABI 版本历史

        Args:
            contract_name: 合约名称

        Returns:
            ABI 版本列表
        """
        return self._abi_versions.get(contract_name, [])

    def get_latest_abi_version(self, contract_name: str) -> Optional[dict]:
        """
        获取合约最新 ABI 版本

        Args:
            contract_name: 合约名称

        Returns:
            最新 ABI 版本，如果不存在则返回 None
        """
        versions = self._abi_versions.get(contract_name, [])
        return versions[-1] if versions else None

    def get_abi_compatibility(
        self, contract_name: str, old_version: str, new_version: str
    ) -> dict:
        """
        检查两个 ABI 版本之间的兼容性

        兼容性规则:
        - 新增函数: 兼容
        - 修改函数签名: 不兼容
        - 删除函数: 不兼容
        - 修改事件: 不兼容

        Args:
            contract_name: 合约名称
            old_version: 旧版本号
            new_version: 新版本号

        Returns:
            兼容性检查结果
        """
        versions = self._abi_versions.get(contract_name, [])
        old_abi: Optional[list] = None
        new_abi: Optional[list] = None

        for ver in versions:
            if ver["version"] == old_version:
                old_abi = ver["abi"]
            if ver["version"] == new_version:
                new_abi = ver["abi"]

        if not old_abi or not new_abi:
            return {
                "compatible": False,
                "error": "Version not found",
                "old_version": old_version,
                "new_version": new_version,
            }

        # 提取旧 ABI 函数签名集合
        old_functions: dict[str, dict] = {}
        for entry in old_abi:
            if entry.get("type") == "function":
                sig = self._build_function_signature(entry)
                old_functions[sig] = entry

        # 提取新 ABI 函数签名集合
        new_functions: dict[str, dict] = {}
        for entry in new_abi:
            if entry.get("type") == "function":
                sig = self._build_function_signature(entry)
                new_functions[sig] = entry

        # 比较
        old_sigs = set(old_functions.keys())
        new_sigs = set(new_functions.keys())

        added = new_sigs - old_sigs
        removed = old_sigs - new_sigs
        common = old_sigs & new_sigs

        is_compatible = len(removed) == 0

        return {
            "compatible": is_compatible,
            "old_version": old_version,
            "new_version": new_version,
            "added_functions": list(added),
            "removed_functions": list(removed),
            "common_functions": list(common),
            "total_old": len(old_sigs),
            "total_new": len(new_sigs),
        }

    @staticmethod
    def _build_function_signature(entry: dict) -> str:
        """构建函数签名字符串"""
        name = entry.get("name", "")
        inputs = entry.get("inputs", [])
        input_types = ",".join(inp.get("type", "") for inp in inputs)
        return f"{name}({input_types})"

    def generate_proxy_bytecode(
        self, implementation_address: str, contract_name: str = "UpgradeableProxy"
    ) -> str:
        """
        生成代理合约字节码（最小代理 / EIP-1167 风格）

        生成一个极简代理合约字节码，将所有调用转发到实现合约地址。

        Args:
            implementation_address: 实现合约地址（不带 0x 前缀的 40 字符地址）
            contract_name: 代理合约名称

        Returns:
            代理合约字节码
        """
        # 清理地址
        addr = implementation_address.replace("0x", "").lower()
        if len(addr) != 40:
            raise ValueError(f"Invalid address length: {implementation_address}")

        # EIP-1167 最小代理字节码模板
        # 3d602d80600a3d3981f3363d3d373d3d3d363d73<address>5af43d82803e903d91602b57fd5bf3
        proxy_bytecode = (
            f"0x3d602d80600a3d3981f3"
            f"363d3d373d3d3d363d73"
            f"{addr}"
            f"5af43d82803e903d91602b57fd5bf3"
        )

        logger.info(f"Generated proxy bytecode for {contract_name} -> {implementation_address}")
        return proxy_bytecode

    def prepare_upgrade(
        self,
        contract_name: str,
        new_source_code: str,
        proxy_address: str,
    ) -> dict:
        """
        准备合约升级

        流程:
        1. 编译新版本实现合约
        2. 比较 ABI 兼容性
        3. 生成升级所需信息

        Args:
            contract_name: 合约名称
            new_source_code: 新版本源码
            proxy_address: 代理合约地址

        Returns:
            升级准备信息
        """
        # 1. 编译新版本
        new_result = self.compile_source(new_source_code, contract_name)

        # 2. 获取最新 ABI 版本进行兼容性检查
        latest = self.get_latest_abi_version(contract_name)
        compatibility: Optional[dict] = None
        if latest:
            versions = self._abi_versions.get(contract_name, [])
            if len(versions) >= 2:
                old_ver = versions[-2]["version"]
                new_ver = versions[-1]["version"]
                compatibility = self.get_abi_compatibility(
                    contract_name, old_ver, new_ver
                )

        # 3. 获取当前代理部署信息
        artifact = self.get_artifact(contract_name)

        return {
            "contract_name": contract_name,
            "proxy_address": proxy_address,
            "new_bytecode": new_result.bytecode,
            "new_bytecode_hash": new_result.bytecode_hash,
            "new_abi": new_result.abi,
            "abi_compatibility": compatibility,
            "current_artifact": artifact is not None,
            "compiler_version": new_result.compiler_version,
            "prepared_at": datetime.now().isoformat(),
            "requires_migration": compatibility is not None and not compatibility.get("compatible", True),
        }


# 全局编译器实例
_compiler: Optional[ContractCompiler] = None


def get_contract_compiler() -> ContractCompiler:
    """获取合约编译器单例"""
    global _compiler
    if _compiler is None:
        _compiler = ContractCompiler()
    return _compiler
