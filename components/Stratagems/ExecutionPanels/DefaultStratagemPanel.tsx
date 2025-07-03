import React, { useImperativeHandle, forwardRef } from 'react';
import { StratagemSpecificPanelProps, StratagemSpecificPanelRef } from './types';

const DefaultStratagemPanel = forwardRef<StratagemSpecificPanelRef, StratagemSpecificPanelProps>((props, ref) => {
  const { stratagemData, currentUserFirstName, currentUserLastName } = props;
  // currentUserFirstName et currentUserLastName ne sont pas utilisés ici, mais sont acceptés pour la cohérence du type.

  useImperativeHandle(ref, () => ({
    getStratagemDetails: () => {
      // Les stratagèmes par défaut peuvent ne pas avoir de détails spécifiques à configurer via l'UI,
      // ou ils pourraient avoir des champs communs comme 'name', 'description', 'durationHours'
      // qui pourraient être ajoutés ici si nécessaire.
      // Pour l'instant, retourne un objet vide ou des valeurs par défaut si applicables.
      const details: Record<string, any> = {};
      // Exemple: si tous les stratagèmes peuvent avoir une durée personnalisée
      // details.durationHours = defaultDurationHours; 
      return details;
    },
    // getCalculatedInfluenceCost: () => { // Removed
    //   // Le coût d'influence pour les panneaux par défaut est généralement juste le coût de base. // Removed
    //   // Si des variantes génériques étaient gérées ici, cela changerait. // Removed
    //   return stratagemData.influenceCostBase; // Removed
    // } // Removed
  }));

  return (
    <div className="p-4 bg-amber-100/50 rounded-md border border-amber-200">
      <p className="text-sm text-amber-700">
        This stratagem ({stratagemData.title}) uses default execution parameters.
      </p>
      {/* 
        Ici, on pourrait ajouter des champs communs si nécessaire, par exemple :
        - Nom personnalisé pour l'instance du stratagème
        - Description personnalisée
        - Durée (si applicable à de nombreux stratagèmes)
      */}
    </div>
  );
});

DefaultStratagemPanel.displayName = 'DefaultStratagemPanel';
export default DefaultStratagemPanel;
