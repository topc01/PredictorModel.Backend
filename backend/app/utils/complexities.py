from fastapi import HTTPException

class ComplexityMapper:
    """
    Centralized mapping between API labels (no tildes) and real names (with tildes).
    
    Real names are used in:
    - CSV files (dataset, predictions, weekly)
    - Directory names in storage
    - Model metadata
    
    API labels are used in:
    - API endpoints (to avoid URL encoding issues with tildes)
    - File paths (to avoid filesystem issues)
    
    Available complexities:
    ┌─────────────────────┬──────────────────────┐
    │ API Label           │ Real Name            │
    ├─────────────────────┼──────────────────────┤
    │ Baja                │ Baja                 │
    │ Media               │ Media                │
    │ Alta                │ Alta                 │
    │ Neonatologia        │ Neonatología         │
    │ Pediatria           │ Pediatría            │
    │ IntePediatrico      │ Inte. Pediátrico     │
    │ Maternidad          │ Maternidad           │
    └─────────────────────┴──────────────────────┘
    """
    
    # Mapping: real_name -> label (for API)
    _COMPLEXITY_MAP = {
        "Baja": "Baja",
        "Media": "Media",
        "Alta": "Alta",
        "Neonatología": "Neonatologia",
        "Pediatría": "Pediatria",
        "Inte. Pediátrico": "IntePediatrico",
        "Maternidad": "Maternidad"
    }
    
    # Reverse mapping: label -> real_name (for internal use)
    _REVERSE_MAP = {v: k for k, v in _COMPLEXITY_MAP.items()}
    
    @classmethod
    def to_label(cls, real_name: str) -> str:
        """
        Convert real name (with tildes) to API label (without tildes).
        
        Args:
            real_name: Real complexity name (e.g., "Neonatología")
            
        Returns:
            API label (e.g., "Neonatologia")
            
        Raises:
            ValueError: If real_name is not a valid complexity
        """
        if real_name not in cls._COMPLEXITY_MAP:
            raise ValueError(
                f"Invalid complexity: {real_name}. "
                f"Valid options: {', '.join(cls._COMPLEXITY_MAP.keys())}"
            )
        return cls._COMPLEXITY_MAP[real_name]
    
    @classmethod
    def to_real_name(cls, label: str) -> str:
        """
        Convert API label (without tildes) to real name (with tildes).
        
        Args:
            label: API label (e.g., "Neonatologia")
            
        Returns:
            Real complexity name (e.g., "Neonatología")
            
        Raises:
            ValueError: If label is not a valid complexity
        """
        if label not in cls._REVERSE_MAP:
            raise ValueError(
                f"Invalid complexity label: {label}. "
                f"Valid options: {', '.join(cls._REVERSE_MAP.keys())}"
            )
        return cls._REVERSE_MAP[label]
    
    @classmethod
    def is_valid_label(cls, label: str) -> bool:
        """Check if a label is valid."""
        is_valid = label in cls._REVERSE_MAP
        if not is_valid:
            raise HTTPException(
              status_code = 422,
              detail = f"Invalid complexity label: {label}. Valid options: {', '.join(cls.get_all_labels())}"
            )
        return is_valid
    
    @classmethod
    def is_valid_real_name(cls, real_name: str) -> bool:
        """Check if a real name is valid."""
        return real_name in cls._COMPLEXITY_MAP
    
    @classmethod
    def get_all_labels(cls) -> list[str]:
        """Get all valid API labels."""
        return list(cls._REVERSE_MAP.keys())
    
    @classmethod
    def get_all_real_names(cls) -> list[str]:
        """Get all valid real names."""
        return list(cls._COMPLEXITY_MAP.keys())
    
    @classmethod
    def parse_from_api(cls, api_input: str) -> str:
        """
        Parse complexity from API input (case-insensitive).
        
        Accepts lowercase labels from API and converts to real name.
        
        Args:
            api_input: Input from API (e.g., "alta", "neonatologia")
            
        Returns:
            Real complexity name (e.g., "Alta", "Neonatología")
            
        Raises:
            ValueError: If input is not valid
        """
        # Try to match case-insensitively
        for label in cls._REVERSE_MAP.keys():
            if label.lower() == api_input.lower():
                return cls.to_real_name(label)
        
        raise ValueError(
            f"Invalid complexity: {api_input}. "
            f"Valid options (case-insensitive): {', '.join(l.lower() for l in cls._REVERSE_MAP.keys())}"
        )
