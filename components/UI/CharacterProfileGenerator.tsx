import React, { useState, useEffect } from 'react';
import { useWalletContext } from './WalletProvider';
import { generateCharacterProfile } from '../../lib/utils/citizenUtils';

interface CharacterProfileGeneratorProps {
  onClose: () => void;
  onGenerated: (profileData: any) => void;
}

const CharacterProfileGenerator: React.FC<CharacterProfileGeneratorProps> = ({ 
  onClose, 
  onGenerated 
}) => {
  const { citizenProfile } = useWalletContext();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedProfile, setGeneratedProfile] = useState<any>(null);
  
  const handleGenerateProfile = async () => {
    if (!citizenProfile) {
      setError('Citizen profile not found');
      return;
    }
    
    setIsGenerating(true);
    setError(null);
    
    try {
      // Get workplace info if available
      const workplace = citizenProfile.workplace ? {
        name: citizenProfile.workplace.name || '',
        type: citizenProfile.workplace.type || ''
      } : undefined;
      
      // Generate the character profile
      const profileJson = generateCharacterProfile({
        firstName: citizenProfile.firstName || '',
        lastName: citizenProfile.lastName || '',
        socialClass: citizenProfile.socialClass || 'Facchini',
        workplace
      });
      
      const profileData = JSON.parse(profileJson);
      setGeneratedProfile(profileData);
      
    } catch (error) {
      console.error('Error generating character profile:', error);
      setError('An error occurred while generating your character profile');
    } finally {
      setIsGenerating(false);
    }
  };
  
  const handleAccept = () => {
    if (generatedProfile) {
      onGenerated(generatedProfile);
    }
    onClose();
  };
  
  useEffect(() => {
    // Auto-generate on component mount
    handleGenerateProfile();
  }, []);
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-amber-50 rounded-lg p-6 max-w-2xl w-full border-2 border-amber-600 shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-serif text-amber-800">Character Profile Generator</h2>
          <button 
            onClick={onClose}
            className="text-amber-600 hover:text-amber-800 p-2 rounded-full hover:bg-amber-100"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {isGenerating ? (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-700"></div>
            <p className="mt-4 text-amber-800">Generating your character profile...</p>
          </div>
        ) : generatedProfile ? (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-medium text-amber-800 mb-1">Personality</h3>
              <p className="text-gray-700 bg-amber-100 p-3 rounded">{generatedProfile.Personality}</p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-amber-800 mb-1">Core Personality Traits</h3>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-green-100 p-2 rounded">
                  <span className="text-sm text-green-800 font-medium">Positive Trait:</span>
                  <p className="text-green-700">{generatedProfile.CorePersonality[0]}</p>
                </div>
                <div className="bg-red-100 p-2 rounded">
                  <span className="text-sm text-red-800 font-medium">Negative Trait:</span>
                  <p className="text-red-700">{generatedProfile.CorePersonality[1]}</p>
                </div>
                <div className="bg-blue-100 p-2 rounded">
                  <span className="text-sm text-blue-800 font-medium">Core Motivation:</span>
                  <p className="text-blue-700">{generatedProfile.CorePersonality[2]}</p>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-amber-800 mb-1">Family Motto</h3>
              <p className="text-gray-700 italic bg-amber-100 p-3 rounded">"{generatedProfile.familyMotto}"</p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-amber-800 mb-1">Coat of Arms</h3>
              <p className="text-gray-700 bg-amber-100 p-3 rounded">{generatedProfile.coatOfArms}</p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-amber-800 mb-1">Portrait Description</h3>
              <p className="text-gray-700 bg-amber-100 p-3 rounded text-sm h-32 overflow-y-auto">
                {generatedProfile.imagePrompt}
              </p>
            </div>
            
            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={handleGenerateProfile}
                className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 transition-colors"
                disabled={isGenerating}
              >
                Regenerate
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAccept}
                className="px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors"
              >
                Accept & Save
              </button>
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-8">
            <p className="text-amber-800">No profile generated yet.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CharacterProfileGenerator;
