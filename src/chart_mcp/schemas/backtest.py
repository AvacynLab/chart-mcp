"""Pydantic models dedicated to the backtest REST endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SmaCrossParams(BaseModel):
    """Parameters used by the simple moving-average crossover strategy."""

    fast_window: int = Field(
        ...,
        alias="fastWindow",
        ge=2,
        le=500,
        description="Lookback window for the fast moving average in candles.",
    )
    slow_window: int = Field(
        ...,
        alias="slowWindow",
        ge=3,
        le=1000,
        description="Lookback window for the slow moving average in candles.",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_order(self) -> "SmaCrossParams":
        """Ensure that the fast window is strictly lower than the slow window."""

        if self.fast_window >= self.slow_window:
            raise ValueError("fastWindow must be strictly less than slowWindow")
        return self


class StrategySpec(BaseModel):
    """Discriminated strategy specification for backtests."""

    name: Literal["sma_cross"] = Field(
        ..., description="Currently supported strategy identifier."
    )
    params: SmaCrossParams = Field(..., description="Strategy parameter payload.")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BacktestRequest(BaseModel):
    """Incoming request body for the backtest endpoint."""

    symbol: str = Field(..., min_length=2, max_length=20, description="Instrument ticker")
    timeframe: str = Field(
        ...,
        pattern="^[0-9]+[mhdw]$",
        description="Candle timeframe such as 1h or 1d.",
    )
    start: int | None = Field(
        None,
        ge=0,
        description="Inclusive start timestamp in seconds for the historical window.",
    )
    end: int | None = Field(
        None,
        ge=0,
        description="Inclusive end timestamp in seconds for the historical window.",
    )
    limit: int = Field(
        1000,
        ge=100,
        le=5000,
        description="Maximum number of candles fetched to run the simulation.",
    )
    fees_bps: float = Field(
        0.0,
        alias="feesBps",
        ge=0.0,
        le=500.0,
        description="Round-trip transaction fees expressed in basis points.",
    )
    slippage_bps: float = Field(
        0.0,
        alias="slippageBps",
        ge=0.0,
        le=500.0,
        description="Slippage per trade expressed in basis points.",
    )
    strategy: StrategySpec = Field(..., description="Trading strategy to evaluate.")

    model_config = ConfigDict(populate_by_name=True, extra="forbid", str_strip_whitespace=True)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        """Normalize the ticker to uppercase to keep cache keys stable."""

        return value.upper()

    @model_validator(mode="after")
    def validate_range(self) -> "BacktestRequest":
        """Ensure the requested time range is coherent when both bounds are provided."""

        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class MetricsModel(BaseModel):
    """Collection of aggregate metrics describing the backtest."""

    total_return: float = Field(..., alias="totalReturn")
    cagr: float = Field(..., alias="cagr")
    max_drawdown: float = Field(..., alias="maxDrawdown")
    win_rate: float = Field(..., alias="winRate")
    sharpe: float = Field(..., alias="sharpe")
    profit_factor: float = Field(..., alias="profitFactor")

    model_config = ConfigDict(populate_by_name=True)


class EquityPoint(BaseModel):
    """Single point of the simulated equity curve."""

    ts: int
    equity: float


class TradeModel(BaseModel):
    """Serialized trade capturing entry/exit details."""

    entry_ts: int = Field(..., alias="entryTs")
    exit_ts: int = Field(..., alias="exitTs")
    entry_price: float = Field(..., alias="entryPrice")
    exit_price: float = Field(..., alias="exitPrice")
    return_pct: float = Field(..., alias="returnPct")

    model_config = ConfigDict(populate_by_name=True)


class BacktestResponse(BaseModel):
    """Complete response body returned by the backtest endpoint."""

    symbol: str
    timeframe: str
    metrics: MetricsModel
    equity_curve: list[EquityPoint] = Field(..., alias="equityCurve")
    trades: list[TradeModel]

    model_config = ConfigDict(populate_by_name=True)
