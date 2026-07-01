from __future__ import annotations

from src.infrastructure.purchases.puc.puc_seed import PUC_SEED_ACCOUNTS


class TestPUCSeedAccounts:
    def test_codes_are_unique(self):
        codes = [account["code"] for account in PUC_SEED_ACCOUNTS]
        assert len(codes) == len(set(codes))

    def test_every_account_has_a_valid_class(self):
        valid_classes = {"activo", "pasivo", "patrimonio", "ingreso", "gasto", "costo"}
        for account in PUC_SEED_ACCOUNTS:
            assert account["account_class"] in valid_classes

    def test_includes_proveedores_and_iva_descontable(self):
        codes = {account["code"] for account in PUC_SEED_ACCOUNTS}
        assert "2205" in codes
        assert "240801" in codes
