"""
配置加载器 — 单例模式，从 config.yaml 加载配置。
支持 config.get('auth.algorithm') 形式的点号路径访问。
"""

import os
import yaml


class _Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    # ------------------------------------------------------------------
    def _load(self):
        if self._loaded:
            return
        cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(cfg_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)
        self._loaded = True

    # ------------------------------------------------------------------
    # 点号路径访问: config.get("auth.algorithm")
    # ------------------------------------------------------------------
    def get(self, key_path: str, default=None):
        self._load()
        keys = key_path.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    # ------------------------------------------------------------------
    # 快捷属性
    # ------------------------------------------------------------------
    @property
    def base_url(self) -> str:
        env_name = self.get("current_env", "test")
        return self.get(f"environments.{env_name}.base_url", "")

    @property
    def timeout(self) -> int:
        env_name = self.get("current_env", "test")
        return self.get(f"environments.{env_name}.timeout", 60)

    @property
    def auth_enabled(self) -> bool:
        return self.get("auth.enabled", False)

    @property
    def auth_algorithm(self) -> str:
        return self.get("auth.algorithm", "RSAWithSHA256")

    @property
    def callback_url(self) -> str:
        return self.get("callback_url", "")

    @property
    def root_dir(self) -> str:
        """项目根目录（config/ 的上级）"""
        return os.path.dirname(os.path.dirname(__file__))


config = _Config()
