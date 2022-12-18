from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Union

import matplotlib.pyplot as plt
import numpy as np
from rich.console import Console
from rich.table import Table
from scipy.interpolate import interp1d
from scipy.optimize import brentq

from concreteproperties.post import plotting_context

if TYPE_CHECKING:
    import matplotlib


@dataclass
class StressStrainProfile:
    """Abstract base class for a material stress-strain profile.

    Implements a piecewise linear stress-strain profile. Positive stresses & strains are
    compression.

    :param strains: List of strains (must be increasing or equal)
    :param stresses: List of stresses
    """

    strains: List[float]
    stresses: List[float]

    def __post_init__(
        self,
    ):
        # validate input - same length lists
        if len(self.strains) != len(self.stresses):
            raise ValueError("Length of strains must equal length of stresses")

        # validate input - length > 1
        if len(self.strains) < 2:
            raise ValueError("Length of strains and stresses must be greater than 1")

        # validate input - increasing values
        prev_strain = self.strains[0]

        for idx in range(len(self.strains)):
            if idx != 0:
                if self.strains[idx] < prev_strain:
                    msg = "strains must contain increasing values."
                    raise ValueError(msg)

                prev_strain = self.strains[idx]

    def get_stress(
        self,
        strain: float,
    ) -> float:
        """Returns a stress given a strain.

        :param strain: Strain at which to return a stress.

        :return: Stress
        """

        # create interpolation function
        stress_function = interp1d(
            x=self.strains,
            y=self.stresses,
            kind="linear",
            fill_value="extrapolate",  # type: ignore
        )

        return stress_function(strain)

    def get_elastic_modulus(
        self,
    ) -> float:
        """Returns the elastic modulus of the stress-strain profile.

        :return: Elastic modulus
        """

        small_strain = 1e-6

        # get stress at zero strain
        stress_0 = self.get_stress(strain=0)

        # get stress at small positive strain & compute elastic modulus
        stress_positive = self.get_stress(strain=small_strain)
        em_positive = stress_positive / small_strain

        # get stress at small negative strain & compute elastic modulus
        stress_negative = self.get_stress(strain=-small_strain)
        em_negative = stress_negative / -small_strain

        # check elastic moduli are equal, if not print warning
        if not np.isclose(em_positive, em_negative):
            warnings.warn(
                "Initial compressive and tensile elastic moduli are not equal"
            )

        if np.isclose(em_positive, 0):
            raise ValueError("Elastic modulus is zero.")

        return em_positive

    def get_compressive_strength(
        self,
    ) -> float:
        """Returns the most positive stress.

        :return: Compressive strength
        """

        return max(self.stresses)

    def get_tensile_strength(
        self,
    ) -> float:
        """Returns the most negative stress.

        :return: Tensile strength
        """

        return min(self.stresses)

    def get_yield_strength(
        self,
    ) -> float:
        """Returns the yield strength of the stress-strain profile.

        :return: Yield strength
        """

        raise NotImplementedError

    def get_ultimate_compressive_strain(
        self,
    ) -> float:
        """Returns the largest compressive strain.

        :return: Ultimate strain
        """

        return max(self.strains)

    def get_ultimate_tensile_strain(
        self,
    ) -> float:
        """Returns the largest tensile strain.

        :return: Ultimate strain
        """

        return min(self.strains)

    def get_unique_strains(
        self,
    ) -> List[float]:
        """Returns an ordered list of unique strains.

        :return: Ordered list of unique strains
        """

        unique_strains = list(set(self.strains))
        unique_strains.sort()

        return unique_strains

    def print_properties(
        self,
        fmt: str = "8.6e",
    ):
        """Prints the stress-strain profile properties to the terminal.

        :param fmt: Number format
        """

        table = Table(title=f"Stress-Strain Profile - {type(self).__name__}")
        table.add_column("Property", justify="left", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        table.add_row(
            "Elastic Modulus", "{:>{fmt}}".format(self.get_elastic_modulus(), fmt=fmt)
        )
        table.add_row(
            "Compressive Strength",
            "{:>{fmt}}".format(self.get_compressive_strength(), fmt=fmt),
        )
        table.add_row(
            "Tensile Strength",
            "{:>{fmt}}".format(-self.get_tensile_strength(), fmt=fmt),
        )
        table.add_row(
            "Ultimate Compressive Strain",
            "{:>{fmt}}".format(self.get_ultimate_compressive_strain(), fmt=fmt),
        )
        table.add_row(
            "Ultimate Tensile Strain",
            "{:>{fmt}}".format(self.get_ultimate_tensile_strain(), fmt=fmt),
        )

        console = Console()
        console.print(table)

    def plot_stress_strain(
        self,
        title: str = "Stress-Strain Profile",
        fmt: str = "o-",
        **kwargs,
    ) -> matplotlib.axes.Axes:  # type: ignore
        """Plots the stress-strain profile.

        :param title: Plot title
        :param fmt: Plot format string
        :param kwargs: Passed to :func:`~concreteproperties.post.plotting_context`

        :return: Matplotlib axes object
        """

        # create plot and setup the plot
        with plotting_context(title=title, **kwargs) as (
            fig,
            ax,
        ):
            ax.plot(self.strains, self.stresses, fmt)  # type: ignore
            plt.xlabel("Strain")
            plt.ylabel("Stress")
            plt.grid(True)

        return ax


@dataclass
class ConcreteServiceProfile(StressStrainProfile):
    """Abstract class for a concrete service stress-strain profile.

    :param strains: List of strains (must be increasing or equal)
    :param stresses: List of stresses
    :param ultimate_strain: Concrete strain at failure
    """

    strains: List[float]
    stresses: List[float]
    elastic_modulus: float = field(init=False)
    ultimate_strain: float

    def print_properties(
        self,
        fmt: str = "8.6e",
    ):
        """Prints the stress-strain profile properties to the terminal.

        :param fmt: Number format
        """

        table = Table(title=f"Stress-Strain Profile - {type(self).__name__}")
        table.add_column("Property", justify="left", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        table.add_row(
            "Elastic Modulus", "{:>{fmt}}".format(self.get_elastic_modulus(), fmt=fmt)
        )
        table.add_row(
            "Ultimate Compressive Strain",
            "{:>{fmt}}".format(self.get_ultimate_compressive_strain(), fmt=fmt),
        )

        console = Console()
        console.print(table)

    def get_elastic_modulus(
        self,
    ) -> float:
        """Returns the elastic modulus of the stress-strain profile.

        :return: Elastic modulus
        """

        try:
            return self.elastic_modulus
        except AttributeError:
            return super().get_elastic_modulus()

    def get_compressive_strength(
        self,
    ) -> Union[float, None]:
        """Returns the most positive stress.

        :return: Compressive strength
        """

        return None

    def get_tensile_strength(
        self,
    ) -> Union[float, None]:
        """Returns the most negative stress.

        :return: Tensile strength
        """

        return None

    def get_ultimate_compressive_strain(
        self,
    ) -> float:
        """Returns the largest strain.

        :return: Ultimate strain
        """

        return self.ultimate_strain


@dataclass
class ConcreteLinear(ConcreteServiceProfile):
    """Class for a symmetric linear stress-strain profile.

    :param elastic_modulus: Elastic modulus of the stress-strain profile
    :param ultimate_strain: Concrete strain at failure
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    elastic_modulus: float
    ultimate_strain: float = field(default=1)

    def __post_init__(
        self,
    ):
        self.strains = [-0.001, 0, 0.001]
        self.stresses = [-0.001 * self.elastic_modulus, 0, 0.001 * self.elastic_modulus]


@dataclass
class ConcreteLinearNoTension(ConcreteServiceProfile):
    """Class for a linear stress-strain profile with no tensile strength.

    :param elastic_modulus: Elastic modulus of the stress-strain profile
    :param ultimate_strain: Concrete strain at failure
    :param compressive_strength: Compressive strength of the concrete
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    elastic_modulus: float
    ultimate_strain: float = field(default=1)
    compressive_strength: Union[float, None] = field(default=None)

    def __post_init__(
        self,
    ):
        self.strains = [-0.001, 0, 0.001]
        self.stresses = [0, 0, 0.001 * self.elastic_modulus]

        if self.compressive_strength is not None:
            self.strains[-1] = self.compressive_strength / self.elastic_modulus
            self.stresses[-1] = self.compressive_strength
            self.strains.append(self.ultimate_strain)
            self.stresses.append(self.compressive_strength)


@dataclass
class EurocodeNonLinear(ConcreteServiceProfile):
    r"""Class for a non-linear stress-strain relationship to EC2.

    Tension is modelled with a symmetric ``elastic_modulus`` until failure at
    ``tensile_strength``, after which the tensile stress reduces according to the
    ``tension_softening_stiffness``.

    :param elastic_modulus: Concrete elastic modulus (:math:`E_{cm}`)
    :param ultimate_strain: Concrete strain at failure (:math:`\epsilon_{cu1}`)
    :param compressive_strength: Concrete compressive strength (:math:`f_{cm}`)
    :param compressive_strain: Strain at which the concrete stress equals the
        compressive strength (:math:`\epsilon_{c1}`)
    :param tensile_strength:  Concrete tensile strength
    :param tension_softening_stiffness: Slope of the linear tension softening
        branch
    :param n_points_1: Number of points to discretise the curve prior to the peak stress
    :param n_points_2: Number of points to discretise the curve after the peak stress
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    elastic_modulus: float
    ultimate_strain: float
    compressive_strength: float
    compressive_strain: float
    tensile_strength: float
    tension_softening_stiffness: float
    n_points_1: int = field(default=10)
    n_points_2: int = field(default=3)

    def __post_init__(
        self,
    ):
        self.strains = []
        self.stresses = []

        # tensile portion of curve
        strain_tension_strength = -self.tensile_strength / self.elastic_modulus
        strain_zero_tension = (
            strain_tension_strength
            - self.tensile_strength / self.tension_softening_stiffness
        )

        self.strains.append(1.1 * strain_zero_tension)
        self.stresses.append(0)
        self.strains.append(strain_zero_tension)
        self.stresses.append(0)
        self.strains.append(strain_tension_strength)
        self.stresses.append(-self.tensile_strength)
        self.strains.append(0)
        self.stresses.append(0)

        # constants
        k = (
            1.05
            * self.elastic_modulus
            * self.compressive_strain
            / self.compressive_strength
        )

        # initialise concrete stress and strain
        conc_strain = 0
        conc_stress = 0

        # prior to peak stress
        for idx in range(self.n_points_1):
            conc_strain = self.compressive_strain / self.n_points_1 * (idx + 1)
            eta = conc_strain / self.compressive_strain
            conc_stress = (
                self.compressive_strength * (k * eta - eta * eta) / (1 + eta * (k - 2))
            )

            self.strains.append(conc_strain)
            self.stresses.append(conc_stress)

        # after peak stress
        for idx in range(self.n_points_2):
            remaining_strain = self.ultimate_strain - self.compressive_strain
            conc_strain = (
                self.compressive_strain + remaining_strain / self.n_points_2 * (idx + 1)
            )
            eta = conc_strain / self.compressive_strain
            conc_stress = (
                self.compressive_strength * (k * eta - eta * eta) / (1 + eta * (k - 2))
            )

            self.strains.append(conc_strain)
            self.stresses.append(conc_stress)

        # close off final stress
        self.strains.append(1.01 * conc_strain)
        self.stresses.append(conc_stress)


@dataclass
class ConcreteUltimateProfile(StressStrainProfile):
    """Abstract class for a concrete ultimate stress-strain profile.

    :param strains: List of strains (must be increasing or equal)
    :param stresses: List of stresses
    :param compressive_strength: Concrete compressive strength
    """

    strains: List[float]
    stresses: List[float]
    compressive_strength: float

    def get_compressive_strength(
        self,
    ) -> float:
        """Returns the most positive stress.

        :return: Compressive strength
        """

        return self.compressive_strength

    def get_ultimate_compressive_strain(
        self,
    ) -> float:
        """Returns the ultimate strain, or largest compressive strain.

        :return: Ultimate strain
        """

        try:
            return self.ultimate_strain  # type: ignore
        except AttributeError:
            return super().get_ultimate_compressive_strain()

    def print_properties(
        self,
        fmt: str = "8.6e",
    ):
        """Prints the stress-strain profile properties to the terminal.

        :param fmt: Number format
        """

        table = Table(title=f"Stress-Strain Profile - {type(self).__name__}")
        table.add_column("Property", justify="left", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        table.add_row(
            "Compressive Strength",
            "{:>{fmt}}".format(self.get_compressive_strength(), fmt=fmt),
        )
        table.add_row(
            "Ultimate Compressive Strain",
            "{:>{fmt}}".format(self.get_ultimate_compressive_strain(), fmt=fmt),
        )
        console = Console()
        console.print(table)


@dataclass
class RectangularStressBlock(ConcreteUltimateProfile):
    """Class for a rectangular stress block.

    :param compressive_strength: Concrete compressive strength
    :param alpha: Factor that modifies the concrete compressive strength
    :param gamma: Factor that modifies the depth of the stress block
    :param ultimate_strain: Concrete strain at failure
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    compressive_strength: float
    alpha: float
    gamma: float
    ultimate_strain: float

    def __post_init__(
        self,
    ):
        self.strains = [
            0,
            self.ultimate_strain * (1 - self.gamma),
            self.ultimate_strain * (1 - self.gamma),
            self.ultimate_strain,
        ]
        self.stresses = [
            0,
            0,
            self.alpha * self.compressive_strength,
            self.alpha * self.compressive_strength,
        ]

    def get_stress(
        self,
        strain: float,
    ) -> float:
        """Returns a stress given a strain.

        Overrides parent method with small tolerance to aid ultimate stress generation
        at nodes.

        :param strain: Strain at which to return a stress.

        :return: Stress
        """

        if strain >= self.strains[1] - 1e-8:
            return self.stresses[2]
        else:
            return 0


@dataclass
class BilinearStressStrain(ConcreteUltimateProfile):
    """Class for a bilinear stress-strain relationship.

    :param compressive_strength: Concrete compressive strength
    :param compressive_strain: Strain at which the concrete stress equals the
        compressive strength
    :param ultimate_strain: Concrete strain at failure
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    compressive_strength: float
    compressive_strain: float
    ultimate_strain: float

    def __post_init__(
        self,
    ):
        self.strains = [
            -self.compressive_strain,
            0,
            self.compressive_strain,
            self.ultimate_strain,
        ]
        self.stresses = [
            0,
            0,
            self.compressive_strength,
            self.compressive_strength,
        ]


@dataclass
class EurocodeParabolicUltimate(ConcreteUltimateProfile):
    """Class for an ultimate parabolic stress-strain relationship to EC2.

    :param compressive_strength: Concrete compressive strength
    :param compressive_strain: Strain at which the concrete stress equals the
        compressive strength
    :param ultimate_strain: Concrete strain at failure
    :param n: Parabolic curve exponent
    :param n_points: Number of points to discretise the parabolic segment of the curve
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    compressive_strength: float
    compressive_strain: float
    ultimate_strain: float
    n: float
    n_points: int = field(default=10)

    def __post_init__(
        self,
    ):
        self.strains = []
        self.stresses = []

        # tensile portion of curve
        self.strains.append(-self.compressive_strain)
        self.stresses.append(0)
        self.strains.append(0)
        self.stresses.append(0)

        # parabolic portion of curve
        for idx in range(self.n_points):
            conc_strain = self.compressive_strain / self.n_points * (idx + 1)
            conc_stress = self.compressive_strength * (
                1 - np.power(1 - (conc_strain / self.compressive_strain), self.n)
            )

            self.strains.append(conc_strain)
            self.stresses.append(conc_stress)

        # compressive plateau
        self.strains.append(self.ultimate_strain)
        self.stresses.append(self.compressive_strength)


@dataclass
class SteelProfile(StressStrainProfile):
    """Abstract class for a steel stress-strain profile.

    :param strains: List of strains (must be increasing or equal)
    :param stresses: List of stresses
    :param yield_strength: Steel yield strength
    :param elastic_modulus: Steel elastic modulus
    :param fracture_strain: Steel fracture strain
    """

    strains: List[float]
    stresses: List[float]
    yield_strength: float
    elastic_modulus: float
    fracture_strain: float

    def get_elastic_modulus(
        self,
    ) -> float:
        """Returns the elastic modulus of the stress-strain profile.

        :return: Elastic modulus
        """

        return self.elastic_modulus

    def get_yield_strength(
        self,
    ) -> float:
        """Returns the yield strength of the stress-strain profile.

        :return: Yield strength
        """

        return self.yield_strength

    def print_properties(
        self,
        fmt: str = "8.6e",
    ):
        """Prints the stress-strain profile properties to the terminal.

        :param fmt: Number format
        """

        table = Table(title=f"Stress-Strain Profile - {type(self).__name__}")
        table.add_column("Property", justify="left", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        table.add_row(
            "Elastic Modulus", "{:>{fmt}}".format(self.get_elastic_modulus(), fmt=fmt)
        )
        table.add_row(
            "Yield Strength", "{:>{fmt}}".format(self.yield_strength, fmt=fmt)
        )
        table.add_row(
            "Tensile Strength",
            "{:>{fmt}}".format(-self.get_tensile_strength(), fmt=fmt),
        )
        table.add_row(
            "Fracture Strain",
            "{:>{fmt}}".format(self.get_ultimate_tensile_strain(), fmt=fmt),
        )

        console = Console()
        console.print(table)


@dataclass
class SteelElasticPlastic(SteelProfile):
    """Class for a perfectly elastic-plastic steel stress-strain profile.

    :param yield_strength: Steel yield strength
    :param elastic_modulus: Steel elastic modulus
    :param fracture_strain: Steel fracture strain
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    yield_strength: float
    elastic_modulus: float
    fracture_strain: float

    def __post_init__(
        self,
    ):
        yield_strain = self.yield_strength / self.elastic_modulus
        self.strains = [
            -self.fracture_strain,
            -yield_strain,
            0,
            yield_strain,
            self.fracture_strain,
        ]
        self.stresses = [
            -self.yield_strength,
            -self.yield_strength,
            0,
            self.yield_strength,
            self.yield_strength,
        ]


@dataclass
class SteelHardening(SteelProfile):
    """Class for a steel stress-strain profile with strain hardening.

    :param yield_strength: Steel yield strength
    :param elastic_modulus: Steel elastic modulus
    :param fracture_strain: Steel fracture strain
    :param ultimate_strength: Steel ultimate strength
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    yield_strength: float
    elastic_modulus: float
    fracture_strain: float
    ultimate_strength: float

    def __post_init__(
        self,
    ):
        yield_strain = self.yield_strength / self.elastic_modulus
        self.strains = [
            -self.fracture_strain,
            -yield_strain,
            0,
            yield_strain,
            self.fracture_strain,
        ]
        self.stresses = [
            -self.ultimate_strength,
            -self.yield_strength,
            0,
            self.yield_strength,
            self.ultimate_strength,
        ]


@dataclass
class StrandProfile(StressStrainProfile):
    """Abstract class for a steel strand stress-strain profile.

    Implements a piecewise linear stress-strain profile. Positive stresses & strains are
    compression.

    :param strains: List of strains (must be increasing or equal)
    :param stresses: List of stresses
    :param yield_strength: Strand yield strength
    """

    strains: List[float]
    stresses: List[float]
    yield_strength: float

    def __post_init__(self) -> None:
        return super().__post_init__()

    def get_strain(
        self,
        stress: float,
    ) -> float:
        """Returns a strain given a stress.

        :param stress: Stress at which to return a strain.

        :return: Strain
        """

        # create interpolation function
        strain_function = interp1d(
            x=self.stresses,
            y=self.strains,
            kind="linear",
            fill_value="extrapolate",  # type: ignore
        )

        return strain_function(stress)

    def get_yield_strength(self) -> float:
        """Returns the yield strength of the stress-strain profile.

        :return: Yield strength
        """

        return self.yield_strength

    def print_properties(
        self,
        fmt: str = "8.6e",
    ) -> None:
        """Prints the stress-strain profile properties to the terminal.

        :param fmt: Number format
        """

        table = Table(title=f"Stress-Strain Profile - {type(self).__name__}")
        table.add_column("Property", justify="left", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        table.add_row(
            "Elastic Modulus", "{:>{fmt}}".format(self.get_elastic_modulus(), fmt=fmt)
        )
        table.add_row(
            "Yield Strength", "{:>{fmt}}".format(self.yield_strength, fmt=fmt)
        )
        table.add_row(
            "Breaking Strength",
            "{:>{fmt}}".format(-self.get_tensile_strength(), fmt=fmt),
        )
        table.add_row(
            "Fracture Strain",
            "{:>{fmt}}".format(self.get_ultimate_tensile_strain(), fmt=fmt),
        )

        console = Console()
        console.print(table)


@dataclass
class StrandHardening(StrandProfile):
    """Class for a strand stress-strain profile with strain hardening.

    :param yield_strength: Strand yield strength
    :param elastic_modulus: Strand elastic modulus
    :param fracture_strain: Strand fracture strain
    :param breaking_strength: Strand breaking strength
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    yield_strength: float
    elastic_modulus: float
    fracture_strain: float
    breaking_strength: float

    def __post_init__(self) -> None:
        yield_strain = self.yield_strength / self.elastic_modulus
        self.strains = [
            -self.fracture_strain,
            -yield_strain,
            0,
            yield_strain,
            self.fracture_strain,
        ]
        self.stresses = [
            -self.breaking_strength,
            -self.yield_strength,
            0,
            self.yield_strength,
            self.breaking_strength,
        ]

        return super().__post_init__()

    def get_elastic_modulus(
        self,
    ) -> float:
        """Returns the elastic modulus of the stress-strain profile.

        :return: Elastic modulus
        """

        return self.elastic_modulus


@dataclass
class StrandPCI1992(StrandProfile):
    """Class for a strand stress-strain profile by R. Devalapura and M. Tadros from the
    March-April issue of the PCI Journal.

    :param yield_strength: Strand yield strength
    :param elastic_modulus: Strand elastic modulus
    :param fracture_strain: Strand fracture strain
    :param breaking_strength: Strand breaking strength
    :param bilinear_yield_ratio: Ratio between the stress at the intersection of a
        bilinear profile, and the yield strength
    :param strain_cps: Strain control points, generates the following strain segments:
        ``[0, strain_cps[0], strain_cps[1], fracture_strain]``. Length must be equal to
        2.
    :param n_points: Number of points to discretise within each strain segment. Length
        must be equal to 3.
    """

    strains: List[float] = field(init=False)
    stresses: List[float] = field(init=False)
    yield_strength: float
    elastic_modulus: float
    fracture_strain: float
    breaking_strength: float
    bilinear_yield_ratio: float = 1.04
    strain_cps: List[float] = field(default_factory=lambda: [0.005, 0.015])
    n_points: List[int] = field(default_factory=lambda: [5, 14, 5])

    def __post_init__(self) -> None:
        # validate control points
        if len(self.strain_cps) != 2:
            raise ValueError("Length of strain_cps must be equal to 2.")

        if len(self.n_points) != 3:
            raise ValueError("Length of n_points must be equal to 3.")

        # determine constants
        f_so = self.bilinear_yield_ratio * self.yield_strength
        const_c = self.elastic_modulus / f_so
        const_a = (
            self.elastic_modulus
            * (self.breaking_strength - f_so)
            / (self.fracture_strain * self.elastic_modulus - f_so)
        )
        const_b = self.elastic_modulus - const_a

        # function that determines the stress
        def stress_eq(a, b, c, d, eps_ps, f_pu):
            if eps_ps != 0:
                sign = eps_ps / abs(eps_ps)  # get sign of strain
            else:
                sign = 1

            eps_ps = abs(eps_ps)  # ensure strain is positive
            denom = pow(1 + pow(c * eps_ps, d), 1 / d)  # calculate denominator
            stress = min(eps_ps * (a + b / denom), f_pu)  # calculate stress

            return sign * stress

        # determine constant D that yields the yield strength at a strain of 0.01
        def find_d(const_d):
            return (
                stress_eq(
                    a=const_a,
                    b=const_b,
                    c=const_c,
                    d=const_d,
                    eps_ps=0.01,
                    f_pu=self.breaking_strength,
                )
                - self.yield_strength
            )

        const_d = brentq(f=find_d, a=1, b=20)

        # generate stresses and strains
        seg1 = np.linspace(
            start=0, stop=self.strain_cps[0], num=self.n_points[0], endpoint=False
        )
        seg2 = np.linspace(
            start=self.strain_cps[0],
            stop=self.strain_cps[1],
            num=self.n_points[1],
            endpoint=False,
        )
        seg3 = np.linspace(
            start=self.strain_cps[1], stop=self.fracture_strain, num=self.n_points[2]
        )
        strain_list = seg1.tolist() + seg2.tolist() + seg3.tolist()

        # generate compressive region of profile
        strains_c = []
        stresses_c = []

        for strain in strain_list:
            strains_c.append(strain)
            stresses_c.append(
                stress_eq(
                    a=const_a,
                    b=const_b,
                    c=const_c,
                    d=const_d,
                    eps_ps=strain,
                    f_pu=self.breaking_strength,
                )
            )

        # generate tensile region of profile
        strains_t = [eps * -1.0 for eps in strains_c[:0:-1]]
        stresses_t = [sig * -1.0 for sig in stresses_c[:0:-1]]

        # combine lists
        self.strains = strains_t + strains_c
        self.stresses = stresses_t + stresses_c

        return super().__post_init__()
