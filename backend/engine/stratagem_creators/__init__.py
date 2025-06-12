# This file makes the 'stratagem_creators' directory a Python package.

from .undercut_stratagem_creator import try_create as try_create_undercut_stratagem
from .coordinate_pricing_stratagem_creator import try_create as try_create_coordinate_pricing_stratagem
from .hoard_resource_stratagem_creator import try_create as try_create_hoard_resource_stratagem
from .political_campaign_stratagem_creator import try_create as try_create_political_campaign_stratagem
# reputation_assault_stratagem_creator is already imported
from .reputation_assault_stratagem_creator import try_create as try_create_reputation_assault_stratagem
from .emergency_liquidation_stratagem_creator import try_create as try_create_emergency_liquidation_stratagem
from .cultural_patronage_stratagem_creator import try_create as try_create_cultural_patronage_stratagem
from .information_network_stratagem_creator import try_create as try_create_information_network_stratagem
from .maritime_blockade_stratagem_creator import try_create as try_create_maritime_blockade_stratagem
from .theater_conspiracy_stratagem_creator import try_create as try_create_theater_conspiracy_stratagem
from .printing_propaganda_stratagem_creator import try_create as try_create_printing_propaganda_stratagem
from .cargo_mishap_stratagem_creator import try_create as try_create_cargo_mishap_stratagem
from .marketplace_gossip_stratagem_creator import try_create as try_create_marketplace_gossip_stratagem
from .employee_poaching_stratagem_creator import try_create as try_create_employee_poaching_stratagem
from .joint_venture_stratagem_creator import try_create as try_create_joint_venture_stratagem
from .canal_mugging_stratagem_creator import try_create as try_create_canal_mugging_stratagem # Added import
# Placeholder for monopoly_pricing
# from .monopoly_pricing_stratagem_creator import try_create as try_create_monopoly_pricing_stratagem
# Placeholder for reputation_boost
# from .reputation_boost_stratagem_creator import try_create as try_create_reputation_boost_stratagem
# Placeholder for burglary
# from .burglary_stratagem_creator import try_create as try_create_burglary_stratagem
# Placeholder for employee_corruption
# from .employee_corruption_stratagem_creator import try_create as try_create_employee_corruption_stratagem
# Placeholder for arson
# from .arson_stratagem_creator import try_create as try_create_arson_stratagem
# Placeholder for charity_distribution
# from .charity_distribution_stratagem_creator import try_create as try_create_charity_distribution_stratagem
# Placeholder for festival_organisation
# from .festival_organisation_stratagem_creator import try_create as try_create_festival_organisation_stratagem

# This dictionary maps stratagem types to their creator functions.
# It will be used by the main engine to dispatch creation requests.
STRATAGEM_CREATORS = {
    "undercut": try_create_undercut_stratagem,
    "coordinate_pricing": try_create_coordinate_pricing_stratagem,
    "hoard_resource": try_create_hoard_resource_stratagem,
    "political_campaign": try_create_political_campaign_stratagem,
    "reputation_assault": try_create_reputation_assault_stratagem, # Already mapped
    "emergency_liquidation": try_create_emergency_liquidation_stratagem,
    "cultural_patronage": try_create_cultural_patronage_stratagem,
    "information_network": try_create_information_network_stratagem,
    "maritime_blockade": try_create_maritime_blockade_stratagem,
    "theater_conspiracy": try_create_theater_conspiracy_stratagem,
    "printing_propaganda": try_create_printing_propaganda_stratagem,
    "cargo_mishap": try_create_cargo_mishap_stratagem,
    "marketplace_gossip": try_create_marketplace_gossip_stratagem,
    "employee_poaching": try_create_employee_poaching_stratagem,
    "joint_venture": try_create_joint_venture_stratagem,
    "canal_mugging": try_create_canal_mugging_stratagem, # Added mapping
    # "monopoly_pricing": try_create_monopoly_pricing_stratagem,
    # "reputation_boost": try_create_reputation_boost_stratagem,
    # "burglary": try_create_burglary_stratagem,
    # "employee_corruption": try_create_employee_corruption_stratagem,
    # "arson": try_create_arson_stratagem,
    # "charity_distribution": try_create_charity_distribution_stratagem,
    # "festival_organisation": try_create_festival_organisation_stratagem,
}
# Import other stratagem creators here as they are developed
