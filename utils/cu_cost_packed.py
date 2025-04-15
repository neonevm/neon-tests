from __future__ import annotations

from typing import Final

from typing_extensions import Self

SOL_SIG_COST: Final[int] = 5_000
SOLANA_MAX_CU_LIMIT = 1_400_000


class NeonProg:
    SignatureGas: Final[int] = SOL_SIG_COST
    BaseGas: Final[int] = SignatureGas + 0

    # Gas-related constants
    MinIterCnt: Final[int] = 3  # Begin + 1-Execution + Finalization
    MinTxCost: Final[int] = 30_000  # Begin(10'000) + 1-Execution(10'000) + Finalization(10'000)


class SolCbProg:
    # CUs limit
    MaxCuLimit: Final[int] = SOLANA_MAX_CU_LIMIT
    # CU prices
    BaseCuPrice: Final[int] = 10_500
    MicroLamport: Final[int] = pow(10, 6)


def _bitmask(size: int) -> int:
    return (1 << size) - 1


class CuCostPktData:
    _BitLenBatch: Final[int] = 2

    _HdrIterCntLen: Final[int] = 3
    _HdrIterCntMask: Final[int] = _bitmask(_HdrIterCntLen)

    _HdrCuPriceLen: Final[int] = 4
    _HdrCuPriceMask: Final[int] = _bitmask(_HdrCuPriceLen)

    _HdrLen: Final[int] = _HdrIterCntLen + _HdrCuPriceLen
    _HdrMask: Final[int] = _bitmask(_HdrLen)

    def __init__(self, base_tx_cost: int, iter_cnt: int, cu_price_mul_coef: int) -> None:
        assert iter_cnt >= NeonProg.MinIterCnt
        assert cu_price_mul_coef >= 0

        self._base_tx_cost = base_tx_cost
        self._iter_cnt = iter_cnt
        self._cu_price_mul_coef = cu_price_mul_coef

    @classmethod
    def from_raw(cls, base_tx_cost: int, iter_cnt: int, cu_price: int) -> Self:
        cu_price_mul_coef = max(cu_price - 1, 0) // SolCbProg.BaseCuPrice
        return cls(base_tx_cost, iter_cnt, cu_price_mul_coef)

    @classmethod
    def unpack(cls, gas_limit: int) -> Self:
        pkt_hdr = (gas_limit & cls._HdrMask) ^ cls._HdrMask

        def unpkt_hdr_len(_pkt: int, _mask: int) -> int:
            value = _pkt & _mask
            return (value + 1) * cls._BitLenBatch

        iter_cnt_len = unpkt_hdr_len(pkt_hdr, cls._HdrIterCntMask)
        cu_price_len = unpkt_hdr_len(pkt_hdr >> cls._HdrIterCntLen, cls._HdrCuPriceMask)

        def unpkt_len(_pkt: int, _mask_len: int) -> int:
            return _pkt & _bitmask(_mask_len)

        pkt_cu_cost_len = iter_cnt_len + cu_price_len
        pkt_cu_cost_mask = _bitmask(pkt_cu_cost_len)
        pkt_cu_cost = ((gas_limit >> cls._HdrLen) & pkt_cu_cost_mask) ^ pkt_cu_cost_mask

        iter_cnt = unpkt_len(pkt_cu_cost, iter_cnt_len)
        total_iter_cnt = iter_cnt + NeonProg.MinIterCnt
        cu_price_mul_coef = unpkt_len(pkt_cu_cost >> iter_cnt_len, cu_price_len)

        tx_cu_cost = cls._calc_tx_cu_cost(cu_price_mul_coef, total_iter_cnt)
        base_tx_cost = gas_limit - tx_cu_cost
        if NeonProg.MinTxCost > base_tx_cost:
            return cls(gas_limit, NeonProg.MinIterCnt, 0)
        elif NeonProg.MinTxCost > (base_tx_cost - NeonProg.BaseGas * iter_cnt):
            return cls(gas_limit, NeonProg.MinIterCnt, 0)

        return cls(base_tx_cost, total_iter_cnt, cu_price_mul_coef)

    @property
    def base_tx_cost(self) -> int:
        return self._base_tx_cost

    @property
    def min_tx_cost(self) -> int:
        return self._base_tx_cost + self._calc_tx_cu_cost(self._cu_price_mul_coef, self._iter_cnt)

    @property
    def iter_cnt(self) -> int:
        return self._iter_cnt

    @property
    def iter_cu_cost(self) -> int:
        return self._calc_iter_cu_cost(self._cu_price_mul_coef)

    @property
    def cu_price(self) -> int:
        return self._calc_cu_price(self._cu_price_mul_coef)

    @property
    def tx_cost(self) -> int:
        pkt_cu_cost = self._pkt_cu_cost
        pkt_cu_cost_len = self._pkt_cu_cost_len
        min_tx_cost = self.min_tx_cost

        high_tx_cost = min_tx_cost >> pkt_cu_cost_len
        if (tx_cost := (high_tx_cost << pkt_cu_cost_len) | pkt_cu_cost) >= min_tx_cost:
            return tx_cost

        bit_len = high_tx_cost.bit_length()
        for i in range(bit_len):
            bit = 1 << i
            if not (high_tx_cost & bit):
                high_tx_cost |= bit
                break
        else:
            high_tx_cost = 1 << bit_len

        return (high_tx_cost << pkt_cu_cost_len) | pkt_cu_cost

    @property
    def tx_cu_cost(self) -> int:
        return self.tx_cost - self._base_tx_cost

    @property
    def _pkt_cu_cost(self) -> int:
        # pack lengths
        pkt_cu_cost = self._pkt_cu_price
        pkt_cu_cost <<= self._pkt_iter_cnt_len
        pkt_cu_cost |= self._pkt_iter_cnt

        # pack offsets
        def calc_hdr_len(value: int) -> int:
            return value // self._BitLenBatch - 1

        pkt_cu_cost <<= self._HdrCuPriceLen
        pkt_cu_cost |= calc_hdr_len(self._pkt_cu_price_len)
        pkt_cu_cost <<= self._HdrIterCntLen
        pkt_cu_cost |= calc_hdr_len(self._pkt_iter_cnt_len)

        return pkt_cu_cost ^ _bitmask(self._pkt_cu_cost_len)

    @property
    def _pkt_cu_cost_len(self) -> int:
        return self._HdrLen + self._pkt_iter_cnt_len + self._pkt_cu_price_len

    @property
    def _pkt_iter_cnt(self) -> int:
        return self._iter_cnt - NeonProg.MinIterCnt

    @property
    def _pkt_iter_cnt_len(self) -> int:
        return self._calc_pkt_len(self._pkt_iter_cnt)

    @property
    def _pkt_cu_price(self) -> int:
        return self._cu_price_mul_coef

    @property
    def _pkt_cu_price_len(self) -> int:
        return self._calc_pkt_len(self._pkt_cu_price)

    @staticmethod
    def _calc_cu_price(cu_price_mul_coef: int) -> int:
        return (cu_price_mul_coef + 1) * SolCbProg.BaseCuPrice

    @classmethod
    def _calc_iter_cu_cost(cls, cu_price_mul_coef: int) -> int:
        return cls._calc_cu_price(cu_price_mul_coef) * SolCbProg.MaxCuLimit // SolCbProg.MicroLamport

    @classmethod
    def _calc_tx_cu_cost(cls, cu_price_mul_coef: int, iter_cnt: int) -> int:
        return cls._calc_iter_cu_cost(cu_price_mul_coef) * iter_cnt

    @classmethod
    def _calc_pkt_len(cls, value: int) -> int:
        return (value.bit_length() // cls._BitLenBatch + 1) * cls._BitLenBatch
