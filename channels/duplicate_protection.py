"""Universal Distribution Fabric — Duplicate Protection

Prevents duplicate publication across platforms.
Uses content hash, product ID, and metadata hash for deduplication.
"""

import hashlib
import json
import os
from typing import Dict, Optional

DEFAULT_REGISTRY_PATH = "data/publication_registry.json"


class DuplicateProtectionError(Exception):
    pass


class DuplicateProtection:
    def __init__(self, registry_path=None):
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self._registry = self._load_registry()

    def _load_registry(self) -> Dict:
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {"publications": {}, "hashes": {}}
        return {"publications": {}, "hashes": {}}

    def _save_registry(self):
        os.makedirs(os.path.dirname(self.registry_path) or ".", exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _content_hash(file_path: str) -> Optional[str]:
        if not file_path or not os.path.exists(file_path):
            return None
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _metadata_hash(product_data: Dict) -> str:
        canonical = json.dumps({
            "title": product_data.get("title", ""),
            "description": product_data.get("description", ""),
            "price": product_data.get("price", 0),
            "product_type": product_data.get("product_type", ""),
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def check_duplicate(self, product_id: str = None, file_path: str = None,
                        metadata: Dict = None, platform: str = None) -> Dict:
        checks = []

        if product_id:
            for pub_id, pub_data in self._registry.get("publications", {}).items():
                if pub_data.get("factory_product_id") == product_id:
                    pub_platform = pub_data.get("platform")
                    # FIX: was checking pub_data["platforms"] (list of dicts) but
                    # register_publication stores pub_data["platform"] (string).
                    # Must compare against actual stored platform string.
                    if not platform or pub_platform == platform:
                        return {"is_duplicate": True, "reason": f"product_id already published",
                                "existing": pub_id, "platform": pub_platform}

        if file_path:
            ch = self._content_hash(file_path)
            if ch and ch in self._registry.get("hashes", {}):
                existing = self._registry["hashes"][ch]
                return {"is_duplicate": True, "reason": "content_hash collision",
                        "existing": existing, "hash": ch}

        if metadata:
            mh = self._metadata_hash(metadata)
            for pub_id, pub_data in self._registry.get("publications", {}).items():
                if pub_data.get("metadata_hash") == mh:
                    return {"is_duplicate": True, "reason": "metadata_hash collision",
                            "existing": pub_id}

        return {"is_duplicate": False, "reason": "no duplicate found"}

    def register_publication(self, factory_product_id: str, platform: str,
                             platform_product_id: str, file_path: str = None,
                             metadata: Dict = None) -> Dict:
        pub_key = f"{factory_product_id}:{platform}"
        if pub_key not in self._registry.get("publications", {}):
            self._registry.setdefault("publications", {})[pub_key] = {
                "factory_product_id": factory_product_id,
                "platform": platform,
                "platform_product_id": platform_product_id,
                "registered_at": __import__("time").time(),
                "metadata_hash": self._metadata_hash(metadata) if metadata else None,
            }
        if file_path:
            ch = self._content_hash(file_path)
            if ch:
                self._registry.setdefault("hashes", {})[ch] = pub_key
        self._save_registry()
        return {"registered": True, "key": pub_key}

    def list_publications(self, factory_product_id: str = None) -> list:
        pubs = []
        for key, data in self._registry.get("publications", {}).items():
            if factory_product_id and data.get("factory_product_id") != factory_product_id:
                continue
            pubs.append(data)
        return pubs
