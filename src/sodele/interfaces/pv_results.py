from pydantic import Field
from sodele.interfaces.base import Base


class PvResult(Base):
    EnergyProfile: list[float] = Field(..., description="The energy profile of the photovoltaic plant.")
    EnergyAreaProfile: list[float] = Field(..., description="The energy profile of the photovoltaic plant per area.")
    SumOfEnergyPerYear: float = Field(..., description="The sum of the energy per year.")
    WorkSpecificEnergyPerYear: float = Field(..., description="The work specific energy per year.")
    AreaSpecificEnergyPerYear: float = Field(..., description="The area specific energy per year.")


class PhotovoltaicResultsWrapper(Base):
    PhotovoltaicPlants: list[PvResult] = Field(..., description="The results of the photovoltaic plants.")
    SummaryOfAllPlants: PvResult = Field(..., description="The summary of all plants.")


class SodeleResults(Base):
    PhotovoltaicResults: PhotovoltaicResultsWrapper = Field(..., description="The results of the photovoltaic simulation.")
