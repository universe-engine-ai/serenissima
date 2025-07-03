import React, { useState, useImperativeHandle, forwardRef, useRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef, CitizenOption, ResourceTypeOption } from './types';
import { FaUser, FaBoxOpen, FaBuilding, FaPercentage, FaCalendarAlt } from 'react-icons/fa';

const SupplierLockoutStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { citizens, buildings, resourceTypes, isLoading } = props;

  // States for Target Resource Type
  const [targetResourceType, setTargetResourceType] = useState<string | null>(null);
  const [resourceTypeSearch, setResourceTypeSearch] = useState('');
  const [isResourceTypeDropdownOpen, setIsResourceTypeDropdownOpen] = useState(false);
  const resourceTypeInputRef = useRef<HTMLInputElement>(null);

  // States for Target Supplier
  const [targetSupplierCitizen, setTargetSupplierCitizen] = useState<string | null>(null);
  const [supplierSearch, setSupplierSearch] = useState('');
  const [isSupplierDropdownOpen, setIsSupplierDropdownOpen] = useState(false);
  const supplierInputRef = useRef<HTMLInputElement>(null);

  // States for Target Building (optional)
  const [targetSupplierBuilding, setTargetSupplierBuilding] = useState<string | null>(null);
  const [buildingSearch, setBuildingSearch] = useState('');
  const [isBuildingDropdownOpen, setIsBuildingDropdownOpen] = useState(false);
  const buildingInputRef = useRef<HTMLInputElement>(null);

  // Premium percentage and duration
  const [premiumPercentage, setPremiumPercentage] = useState<number>(15);
  const [contractDurationDays, setContractDurationDays] = useState<number>(30);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      if (!targetResourceType || !targetSupplierCitizen) {
        console.error("SupplierLockoutStratagemPanel: Target Resource Type and Supplier are required.");
        return null;
      }
      const details: Record<string, any> = {
        targetResourceType,
        targetSupplierCitizen,
        premiumPercentage,
        contractDurationDays,
      };
      if (targetSupplierBuilding) {
        details.targetSupplierBuilding = targetSupplierBuilding;
      }
      return details;
    },
  }));

  // Filter resource types
  const filteredResourceTypes = resourceTypes.filter(rt =>
    rt.name.toLowerCase().includes(resourceTypeSearch.toLowerCase()) ||
    rt.id.toLowerCase().includes(resourceTypeSearch.toLowerCase())
  );

  // Filter citizens for suppliers
  const filteredSuppliers = citizens.filter(c =>
    c.username.toLowerCase().includes(supplierSearch.toLowerCase()) ||
    `${c.firstName} ${c.lastName}`.toLowerCase().includes(supplierSearch.toLowerCase())
  );

  // Filter buildings (only show if supplier is selected)
  const supplierBuildings = targetSupplierCitizen
    ? buildings.filter(b => b.owner === targetSupplierCitizen)
    : [];
  
  const filteredBuildings = supplierBuildings.filter(b =>
    b.name?.toLowerCase().includes(buildingSearch.toLowerCase()) ||
    b.buildingId.toLowerCase().includes(buildingSearch.toLowerCase())
  );

  return (
    <div>
      {/* Target Resource Type */}
      <div className="mb-4">
        <label htmlFor="supplier_lockout_resource" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaBoxOpen className="mr-2" /> Target Resource Type <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="supplier_lockout_resource"
            type="text"
            ref={resourceTypeInputRef}
            value={resourceTypeSearch}
            onChange={(e) => setResourceTypeSearch(e.target.value)}
            onFocus={() => setIsResourceTypeDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsResourceTypeDropdownOpen(false), 200)}
            placeholder="Search for resource type..."
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
            disabled={isLoading}
          />
          {targetResourceType && (
            <div className="mt-1 text-sm text-amber-700">
              Selected: <span className="font-semibold">{resourceTypes.find(rt => rt.id === targetResourceType)?.name || targetResourceType}</span>
            </div>
          )}
          {isResourceTypeDropdownOpen && filteredResourceTypes.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-amber-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
              {filteredResourceTypes.map((rt) => (
                <div
                  key={rt.id}
                  onMouseDown={() => {
                    setTargetResourceType(rt.id);
                    setResourceTypeSearch(rt.name);
                    setIsResourceTypeDropdownOpen(false);
                  }}
                  className="p-2 hover:bg-amber-100 cursor-pointer border-b border-amber-200"
                >
                  <div className="font-medium text-amber-900">{rt.name}</div>
                  <div className="text-sm text-amber-600">{rt.category}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Target Supplier */}
      <div className="mb-4">
        <label htmlFor="supplier_lockout_supplier" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaUser className="mr-2" /> Target Supplier <span className="text-red-500 ml-1">*</span>
        </label>
        <div className="relative">
          <input
            id="supplier_lockout_supplier"
            type="text"
            ref={supplierInputRef}
            value={supplierSearch}
            onChange={(e) => setSupplierSearch(e.target.value)}
            onFocus={() => setIsSupplierDropdownOpen(true)}
            onBlur={() => setTimeout(() => setIsSupplierDropdownOpen(false), 200)}
            placeholder="Search for supplier..."
            className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
            disabled={isLoading}
          />
          {targetSupplierCitizen && (
            <div className="mt-1 text-sm text-amber-700">
              Selected: <span className="font-semibold">{targetSupplierCitizen}</span>
            </div>
          )}
          {isSupplierDropdownOpen && filteredSuppliers.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-amber-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
              {filteredSuppliers.map((citizen) => (
                <div
                  key={citizen.username}
                  onMouseDown={() => {
                    setTargetSupplierCitizen(citizen.username);
                    setSupplierSearch(`${citizen.firstName} ${citizen.lastName} (${citizen.username})`);
                    setIsSupplierDropdownOpen(false);
                    // Reset building selection when supplier changes
                    setTargetSupplierBuilding(null);
                    setBuildingSearch('');
                  }}
                  className="p-2 hover:bg-amber-100 cursor-pointer border-b border-amber-200"
                >
                  <div className="font-medium text-amber-900">
                    {citizen.firstName} {citizen.lastName}
                  </div>
                  <div className="text-sm text-amber-600">
                    @{citizen.username} • {citizen.socialClass}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Target Building (optional) */}
      {targetSupplierCitizen && (
        <div className="mb-4">
          <label htmlFor="supplier_lockout_building" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
            <FaBuilding className="mr-2" /> Target Building (Optional)
          </label>
          <div className="relative">
            <input
              id="supplier_lockout_building"
              type="text"
              ref={buildingInputRef}
              value={buildingSearch}
              onChange={(e) => setBuildingSearch(e.target.value)}
              onFocus={() => setIsBuildingDropdownOpen(true)}
              onBlur={() => setTimeout(() => setIsBuildingDropdownOpen(false), 200)}
              placeholder="Search for building..."
              className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
              disabled={isLoading || supplierBuildings.length === 0}
            />
            {supplierBuildings.length === 0 && (
              <div className="mt-1 text-sm text-amber-600 italic">
                No buildings owned by this supplier
              </div>
            )}
            {targetSupplierBuilding && (
              <div className="mt-1 text-sm text-amber-700">
                Selected: <span className="font-semibold">{buildings.find(b => b.buildingId === targetSupplierBuilding)?.name || targetSupplierBuilding}</span>
              </div>
            )}
            {isBuildingDropdownOpen && filteredBuildings.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-amber-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                {filteredBuildings.map((building) => (
                  <div
                    key={building.buildingId}
                    onMouseDown={() => {
                      setTargetSupplierBuilding(building.buildingId);
                      setBuildingSearch(building.name || building.buildingId);
                      setIsBuildingDropdownOpen(false);
                    }}
                    className="p-2 hover:bg-amber-100 cursor-pointer border-b border-amber-200"
                  >
                    <div className="font-medium text-amber-900">{building.name || building.buildingId}</div>
                    <div className="text-sm text-amber-600">{building.type}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Premium Percentage */}
      <div className="mb-4">
        <label htmlFor="supplier_lockout_premium" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaPercentage className="mr-2" /> Premium Percentage
        </label>
        <input
          id="supplier_lockout_premium"
          type="number"
          min="0"
          max="100"
          value={premiumPercentage}
          onChange={(e) => setPremiumPercentage(Math.max(0, Math.min(100, parseInt(e.target.value) || 0)))}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        />
        <p className="text-sm text-amber-600 mt-1">
          Price premium above market rate: {premiumPercentage}%
        </p>
      </div>

      {/* Contract Duration */}
      <div className="mb-4">
        <label htmlFor="supplier_lockout_duration" className="block text-sm font-medium text-amber-800 mb-1 flex items-center">
          <FaCalendarAlt className="mr-2" /> Contract Duration (Days)
        </label>
        <input
          id="supplier_lockout_duration"
          type="number"
          min="1"
          max="365"
          value={contractDurationDays}
          onChange={(e) => setContractDurationDays(Math.max(1, Math.min(365, parseInt(e.target.value) || 1)))}
          className="w-full p-2 border border-amber-300 rounded-md bg-white text-amber-900 focus:ring-amber-500 focus:border-amber-500"
          disabled={isLoading}
        />
        <p className="text-sm text-amber-600 mt-1">
          Exclusive supply agreement duration: {contractDurationDays} days
        </p>
      </div>

      {/* Summary */}
      <div className="mt-4 p-3 bg-amber-100 border border-amber-300 rounded-md">
        <h4 className="font-semibold text-amber-800 mb-2">Contract Summary</h4>
        <div className="text-sm text-amber-700 space-y-1">
          <p>• Resource: <span className="font-medium">{resourceTypes.find(rt => rt.id === targetResourceType)?.name || 'Not selected'}</span></p>
          <p>• Supplier: <span className="font-medium">{targetSupplierCitizen || 'Not selected'}</span></p>
          <p>• Premium: <span className="font-medium">{premiumPercentage}% above market</span></p>
          <p>• Duration: <span className="font-medium">{contractDurationDays} days</span></p>
          <p className="italic text-amber-600 mt-2">
            This will prevent the supplier from selling to others during the contract period.
          </p>
        </div>
      </div>
    </div>
  );
});

SupplierLockoutStratagemPanel.displayName = 'SupplierLockoutStratagemPanel';

export default SupplierLockoutStratagemPanel;