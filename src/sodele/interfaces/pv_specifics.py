from sodele.interfaces.base import Base
from pydantic import Field

from sodele.misc.database import get_database_paths


class PhotovoltaicPlant(Base):
    uid: str = Field(..., description="The unique identifier of the photovoltaic plant.")
    surfaceAzimuth: float = Field(0, description="The surface azimuth of the photovoltaic plant.")
    surfaceTilt: float = Field(0, description="The surface tilt of the photovoltaic plant.")
    modulesPerString: float = Field(0, description="The number of modules per string.")
    stringsPerInverter: int = Field(0, description="The number of strings per inverter.")
    numberOfInverters: int = Field(0, description="The number of inverters.")
    albedo: float = Field(0.2, description="The albedo of the surface.")
    moduleInstallation: int = Field(1, description="The module installation type.")
    moduleName: str = Field(..., description="The name of the module.")
    lossesIrradiation: float = Field(1.0, description="The losses due to irradiation.")
    lossesDCDatasheet: float = Field(2.0, description="The losses due to the datasheet.")
    lossesDCCables: float = Field(0.0, description="The losses due to the cables.")
    modulesDatabaseType: int = Field(1, description="The type of the modules database. (1 = CEC, 2 = Sandia)")
    useInverterDatabase: bool = Field(False, description="Whether to use the inverter database.")
    inverterName: str = Field(..., description="The name of the inverter.")
    useStandByPowerInverter: bool = Field(False, description="Whether to use the standby power inverter.")
    inverterEta: float = Field(0.92, description="The efficiency of the inverter.")

    energyProfile: list[float] | None = Field(None, description="The energy profile of the photovoltaic plant.")
    surfaceArea: float | None = Field(None, description="The surface area of the photovoltaic plant.")
    systemKWP: float | None = Field(None, description="The system KWP of the photovoltaic plant.")

    @property
    def energyProfileSum(self) -> float:
        if self.energyProfile is None:
            return 0
        return sum(self.energyProfile)

    @property
    def energyProfileArea(self) -> list[float]:
        if self.energyProfile is None:
            return []
        if self.surfaceArea is None:
            return []
        return [energyProfileValue / self.surfaceArea for energyProfileValue in self.energyProfile]

    @property
    def energyProfileAreaSum(self) -> float:
        if self.surfaceArea is None:
            return 0
        if self.energyProfile is None:
            return 0
        return self.energyProfileSum / self.surfaceArea

    @property
    def energyKWPSum(self) -> float:
        if self.systemKWP is None:
            return 0
        if self.energyProfile is None:
            return 0
        return self.energyProfileSum / self.systemKWP

    @property
    def modulesDatabasePath(self) -> str:
        return get_database_paths(self.modulesDatabaseType)[0]

    @property
    def invertersDatabasePath(self) -> str:
        return get_database_paths(self.modulesDatabaseType)[1]
