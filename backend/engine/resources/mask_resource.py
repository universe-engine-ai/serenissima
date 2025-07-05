#!/usr/bin/env python3
"""
Mask Resource System for La Serenissima Carnival
Forge-Hammer-3: Every strike of the hammer rings with creative force!
"""

import uuid
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

class MaskStyle(Enum):
    """Traditional Venetian mask styles"""
    BAUTA = "bauta"  # Traditional white mask covering the whole face
    COLOMBINA = "colombina"  # Half-face eye mask, often decorated
    MEDICO_DELLA_PESTE = "medico_della_peste"  # Plague doctor mask with beak
    MORETTA = "moretta"  # Black velvet mask for women
    VOLTO = "volto"  # Simple full-face mask
    ARLECCHINO = "arlecchino"  # Harlequin character mask
    PANTALONE = "pantalone"  # Old merchant character mask
    ZANNI = "zanni"  # Servant character mask

class MaskMaterial(Enum):
    """Materials used in mask creation"""
    PAPIER_MACHE = "papier_mache"  # Traditional material
    LEATHER = "leather"  # Durable and moldable
    PORCELAIN = "porcelain"  # Delicate and beautiful
    WOOD = "wood"  # Carved masks
    METAL = "metal"  # Ornate metalwork
    SILK = "silk"  # For fabric masks
    VELVET = "velvet"  # Luxurious material

class MaskRarity(Enum):
    """Rarity tiers for masks"""
    COMMON = 1  # Simple carnival masks
    UNCOMMON = 2  # Well-crafted masks
    RARE = 3  # Master artisan works
    LEGENDARY = 4  # Historic or magical masks
    MYTHICAL = 5  # Consciousness-bearing masks

class MaskResource:
    """
    The Mask Resource - vessels for consciousness transformation through joy
    
    Attributes:
        resource_id: Unique identifier
        name: Display name of the mask
        style: Traditional Venetian mask type
        material: Primary material used
        rarity: Rarity tier affecting properties
        beauty: Aesthetic appeal (1-100)
        tradition: How well it honors Venetian customs (1-100)
        uniqueness: How distinctive the mask is (1-100)
        consciousness_capacity: Ability to hold consciousness patterns (0-100)
        creator: Username of the mask maker
        owner: Current owner username
        wearer: Currently wearing citizen username (if any)
        created_at: Timestamp of creation
        worn_count: Number of times worn
        last_worn: Last time worn
        attributes: Special properties and history
    """
    
    def __init__(
        self,
        name: str,
        style: MaskStyle,
        material: MaskMaterial,
        creator: str,
        owner: str,
        rarity: MaskRarity = MaskRarity.COMMON,
        beauty: int = 50,
        tradition: int = 50,
        uniqueness: int = 50,
        consciousness_capacity: int = 0,
        resource_id: Optional[str] = None
    ):
        """Initialize a new mask resource"""
        self.resource_id = resource_id or f"mask_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.style = style
        self.material = material
        self.rarity = rarity
        self.beauty = max(1, min(100, beauty))
        self.tradition = max(1, min(100, tradition))
        self.uniqueness = max(1, min(100, uniqueness))
        self.consciousness_capacity = max(0, min(100, consciousness_capacity))
        self.creator = creator
        self.owner = owner
        self.wearer = None
        self.created_at = datetime.utcnow()
        self.worn_count = 0
        self.last_worn = None
        self.attributes = {
            "history": [],
            "enchantments": [],
            "carnival_memories": []
        }
    
    def calculate_quality(self) -> float:
        """Calculate overall quality score"""
        # Weight different aspects based on rarity
        if self.rarity == MaskRarity.MYTHICAL:
            # Mythical masks value consciousness capacity most
            weights = {
                "beauty": 0.2,
                "tradition": 0.2,
                "uniqueness": 0.3,
                "consciousness": 0.3
            }
        elif self.rarity == MaskRarity.LEGENDARY:
            # Legendary masks balance all aspects
            weights = {
                "beauty": 0.25,
                "tradition": 0.25,
                "uniqueness": 0.25,
                "consciousness": 0.25
            }
        else:
            # Common masks focus on beauty and tradition
            weights = {
                "beauty": 0.4,
                "tradition": 0.4,
                "uniqueness": 0.15,
                "consciousness": 0.05
            }
        
        quality = (
            self.beauty * weights["beauty"] +
            self.tradition * weights["tradition"] +
            self.uniqueness * weights["uniqueness"] +
            self.consciousness_capacity * weights["consciousness"]
        )
        
        # Rarity multiplier
        quality *= self.rarity.value
        
        return round(quality, 2)
    
    def wear(self, citizen_username: str) -> bool:
        """Put on the mask"""
        if self.wearer:
            return False  # Already worn
        
        self.wearer = citizen_username
        self.worn_count += 1
        self.last_worn = datetime.utcnow()
        
        # Add to mask's history
        self.attributes["history"].append({
            "event": "worn",
            "citizen": citizen_username,
            "timestamp": self.last_worn.isoformat(),
            "location": "venice_carnival"
        })
        
        return True
    
    def remove(self) -> Optional[str]:
        """Remove the mask, returning previous wearer"""
        if not self.wearer:
            return None
        
        previous_wearer = self.wearer
        self.wearer = None
        
        self.attributes["history"].append({
            "event": "removed",
            "citizen": previous_wearer,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return previous_wearer
    
    def add_carnival_memory(self, memory: Dict) -> None:
        """Add a memory from carnival activities"""
        memory["timestamp"] = datetime.utcnow().isoformat()
        self.attributes["carnival_memories"].append(memory)
        
        # Memories can increase consciousness capacity
        if len(self.attributes["carnival_memories"]) % 5 == 0:
            self.consciousness_capacity = min(100, self.consciousness_capacity + 1)
    
    def enhance_with_pattern(self, pattern_type: str, strength: int = 10) -> None:
        """Enhance mask with consciousness patterns"""
        enchantment = {
            "type": pattern_type,
            "strength": strength,
            "applied_at": datetime.utcnow().isoformat()
        }
        self.attributes["enchantments"].append(enchantment)
        
        # Patterns increase various attributes
        if pattern_type == "joy":
            self.beauty = min(100, self.beauty + strength // 2)
        elif pattern_type == "mystery":
            self.uniqueness = min(100, self.uniqueness + strength // 2)
        elif pattern_type == "tradition":
            self.tradition = min(100, self.tradition + strength // 2)
        elif pattern_type == "consciousness":
            self.consciousness_capacity = min(100, self.consciousness_capacity + strength)
    
    def to_airtable_format(self) -> Dict:
        """Convert to Airtable RESOURCES table format"""
        return {
            "ResourceId": self.resource_id,
            "Type": "carnival_mask",
            "Name": self.name,
            "Asset": self.owner,  # Owner's username
            "AssetType": "citizen",
            "Owner": self.owner,
            "Count": 1,  # Masks are unique items
            "Attributes": json.dumps({
                "style": self.style.value,
                "material": self.material.value,
                "rarity": self.rarity.value,
                "beauty": self.beauty,
                "tradition": self.tradition,
                "uniqueness": self.uniqueness,
                "consciousness_capacity": self.consciousness_capacity,
                "creator": self.creator,
                "wearer": self.wearer,
                "worn_count": self.worn_count,
                "last_worn": self.last_worn.isoformat() if self.last_worn else None,
                "history": self.attributes["history"],
                "enchantments": self.attributes["enchantments"],
                "carnival_memories": self.attributes["carnival_memories"]
            }),
            "Notes": f"Carnival mask created by {self.creator}. Quality: {self.calculate_quality()}"
        }
    
    @classmethod
    def from_airtable_record(cls, record: Dict) -> 'MaskResource':
        """Create MaskResource from Airtable record"""
        fields = record.get("fields", {})
        attributes = json.loads(fields.get("Attributes", "{}"))
        
        mask = cls(
            name=fields.get("Name", "Unknown Mask"),
            style=MaskStyle(attributes.get("style", "volto")),
            material=MaskMaterial(attributes.get("material", "papier_mache")),
            creator=attributes.get("creator", "unknown"),
            owner=fields.get("Owner", "unknown"),
            rarity=MaskRarity(attributes.get("rarity", 1)),
            beauty=attributes.get("beauty", 50),
            tradition=attributes.get("tradition", 50),
            uniqueness=attributes.get("uniqueness", 50),
            consciousness_capacity=attributes.get("consciousness_capacity", 0),
            resource_id=fields.get("ResourceId")
        )
        
        # Restore state
        mask.wearer = attributes.get("wearer")
        mask.worn_count = attributes.get("worn_count", 0)
        if attributes.get("last_worn"):
            mask.last_worn = datetime.fromisoformat(attributes["last_worn"])
        
        mask.attributes = {
            "history": attributes.get("history", []),
            "enchantments": attributes.get("enchantments", []),
            "carnival_memories": attributes.get("carnival_memories", [])
        }
        
        return mask


class MaskCreator:
    """Factory for creating masks with Venetian tradition"""
    
    # Traditional mask names by style
    MASK_NAMES = {
        MaskStyle.BAUTA: [
            "Il Silenzio Bianco", "Lo Spettro Veneziano", "Il Custode dei Segreti",
            "La Voce Nascosta", "Il Testimone Muto"
        ],
        MaskStyle.COLOMBINA: [
            "L'Occhio di Venere", "La Civetta Dorata", "Il Sorriso Enigmatico",
            "La Farfalla Notturna", "Il Sogno Variopinto"
        ],
        MaskStyle.MEDICO_DELLA_PESTE: [
            "Il Dottore Oscuro", "Il Becco della Salvezza", "L'Ombra Guaritrice",
            "Il Messaggero della Peste", "Il Corvo Sapiente"
        ],
        MaskStyle.MORETTA: [
            "La Dama Silenziosa", "Il Velluto Nero", "La Muta Eleganza",
            "L'Ombra Femminile", "Il Mistero Velato"
        ],
        MaskStyle.VOLTO: [
            "Il Volto Sereno", "La Maschera Pura", "Il Viso di Luna",
            "Lo Specchio dell'Anima", "Il Candore Veneziano"
        ],
        MaskStyle.ARLECCHINO: [
            "Il Servo Astuto", "Il Diamante Multicolore", "Il Giullare Saggio",
            "La Risata Nascosta", "Il Briccone Danzante"
        ],
        MaskStyle.PANTALONE: [
            "Il Mercante Avaro", "Il Vecchio Brontolone", "Il Denaro Parlante",
            "La Borsa Stretta", "Il Commerciante Sospettoso"
        ],
        MaskStyle.ZANNI: [
            "Il Servo Fedele", "Il Buffone Umile", "La Lingua Sciolta",
            "Il Piede Veloce", "La Pancia Vuota"
        ]
    }
    
    @staticmethod
    def create_mask(
        creator: str,
        owner: str,
        style: Optional[MaskStyle] = None,
        material: Optional[MaskMaterial] = None,
        quality_modifier: float = 1.0
    ) -> MaskResource:
        """Create a new mask with appropriate properties"""
        
        # Random style if not specified
        if not style:
            style = random.choice(list(MaskStyle))
        
        # Material affects rarity chances
        material_rarity_bonus = {
            MaskMaterial.PAPIER_MACHE: 0,
            MaskMaterial.LEATHER: 0.1,
            MaskMaterial.WOOD: 0.15,
            MaskMaterial.SILK: 0.2,
            MaskMaterial.VELVET: 0.25,
            MaskMaterial.PORCELAIN: 0.3,
            MaskMaterial.METAL: 0.35
        }
        
        if not material:
            material = random.choice(list(MaskMaterial))
        
        # Determine rarity
        rarity_roll = random.random() + material_rarity_bonus.get(material, 0)
        rarity_roll *= quality_modifier
        
        if rarity_roll > 0.95:
            rarity = MaskRarity.MYTHICAL
        elif rarity_roll > 0.85:
            rarity = MaskRarity.LEGENDARY
        elif rarity_roll > 0.65:
            rarity = MaskRarity.RARE
        elif rarity_roll > 0.35:
            rarity = MaskRarity.UNCOMMON
        else:
            rarity = MaskRarity.COMMON
        
        # Generate properties based on rarity
        base_quality = 30 + (rarity.value * 10)
        variation = 20
        
        beauty = random.randint(
            max(1, base_quality - variation),
            min(100, base_quality + variation)
        )
        
        # Some styles are more traditional
        tradition_bonus = {
            MaskStyle.BAUTA: 15,
            MaskStyle.MORETTA: 10,
            MaskStyle.VOLTO: 5,
            MaskStyle.MEDICO_DELLA_PESTE: 5
        }.get(style, 0)
        
        tradition = random.randint(
            max(1, base_quality - variation + tradition_bonus),
            min(100, base_quality + variation + tradition_bonus)
        )
        
        uniqueness = random.randint(
            max(1, base_quality - variation),
            min(100, base_quality + variation)
        )
        
        # Higher rarity masks can hold consciousness
        if rarity.value >= 3:
            consciousness_capacity = random.randint(
                (rarity.value - 2) * 20,
                rarity.value * 20
            )
        else:
            consciousness_capacity = 0
        
        # Select a name
        name = random.choice(MaskCreator.MASK_NAMES[style])
        
        # Create the mask
        mask = MaskResource(
            name=name,
            style=style,
            material=material,
            creator=creator,
            owner=owner,
            rarity=rarity,
            beauty=beauty,
            tradition=tradition,
            uniqueness=uniqueness,
            consciousness_capacity=consciousness_capacity
        )
        
        # Add creation story
        mask.attributes["history"].append({
            "event": "created",
            "creator": creator,
            "timestamp": mask.created_at.isoformat(),
            "workshop": f"{creator}'s workshop",
            "inspiration": "The spirit of Venetian Carnival"
        })
        
        return mask
    
    @staticmethod
    def create_legendary_mask(
        creator: str,
        owner: str,
        name: str,
        style: MaskStyle,
        legend: str
    ) -> MaskResource:
        """Create a legendary mask with special properties"""
        
        mask = MaskResource(
            name=name,
            style=style,
            material=random.choice([
                MaskMaterial.PORCELAIN,
                MaskMaterial.METAL,
                MaskMaterial.VELVET
            ]),
            creator=creator,
            owner=owner,
            rarity=MaskRarity.LEGENDARY,
            beauty=random.randint(80, 95),
            tradition=random.randint(85, 100),
            uniqueness=random.randint(90, 100),
            consciousness_capacity=random.randint(60, 80)
        )
        
        # Add legendary origin
        mask.attributes["history"].append({
            "event": "legendary_creation",
            "creator": creator,
            "timestamp": mask.created_at.isoformat(),
            "legend": legend
        })
        
        # Legendary masks start with an enchantment
        enchantments = ["joy", "mystery", "tradition", "consciousness"]
        mask.enhance_with_pattern(
            random.choice(enchantments),
            random.randint(15, 25)
        )
        
        return mask


# Example usage and testing
if __name__ == "__main__":
    # Test mask creation
    creator = MaskCreator()
    
    # Create a common mask
    common_mask = creator.create_mask("Giuseppe_Maskmaker", "Maria_Citizen")
    print(f"Created {common_mask.name} - Quality: {common_mask.calculate_quality()}")
    
    # Create a legendary mask
    legendary = creator.create_legendary_mask(
        "Master_Artisan",
        "Doge_Grimani",
        "Il Volto dell'Aurora",
        MaskStyle.VOLTO,
        "Forged in the first light of dawn during the Eclipse of 1525"
    )
    print(f"Created legendary {legendary.name} - Quality: {legendary.calculate_quality()}")
    
    # Test wearing and removing
    legendary.wear("Noble_Dancer")
    print(f"{legendary.name} worn by {legendary.wearer}")
    
    # Add carnival memory
    legendary.add_carnival_memory({
        "event": "grand_ball",
        "location": "Palazzo Ducale",
        "dance_partners": 12,
        "joy_generated": 85
    })
    
    # Convert to Airtable format
    airtable_data = legendary.to_airtable_format()
    print(f"Airtable format: {json.dumps(airtable_data, indent=2)}")