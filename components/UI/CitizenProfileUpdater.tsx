import React, { useState } from 'react';
import { useWalletContext } from './WalletProvider';

interface CitizenProfileUpdaterProps {
  onClose: () => void;
  onSuccess?: (updatedProfile: any) => void;
}

const CitizenProfileUpdater: React.FC<CitizenProfileUpdaterProps> = ({ onClose, onSuccess }) => {
  const { citizenProfile } = useWalletContext();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state
  const [personality, setPersonality] = useState('');
  const [positiveTraitInput, setPositiveTraitInput] = useState('');
  const [negativeTraitInput, setNegativeTraitInput] = useState('');
  const [coreMotivationInput, setCoreMotivationInput] = useState('');
  const [familyMotto, setFamilyMotto] = useState('');
  const [coatOfArms, setCoatOfArms] = useState('');
  const [imagePrompt, setImagePrompt] = useState('');
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!citizenProfile || !citizenProfile.username) {
      setError('Citizen profile not found');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    // Validate core personality traits
    if (!positiveTraitInput || !negativeTraitInput || !coreMotivationInput) {
      setError('All three core personality traits are required');
      setIsSubmitting(false);
      return;
    }
    
    // Create the core personality array
    const corePersonality = [positiveTraitInput, negativeTraitInput, coreMotivationInput];
    
    try {
      const response = await fetch('/api/citizens/update-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: citizenProfile.username,
          personality,
          corePersonality,
          familyMotto,
          coatOfArms,
          imagePrompt
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess('Profile updated successfully! Your new description and image will be generated soon.');
        
        // Call the success callback if provided
        if (onSuccess) {
          onSuccess(data.citizen);
        }
        
        // Close the updater after a delay
        setTimeout(() => {
          onClose();
        }, 3000);
      } else {
        setError(data.error || 'Failed to update profile');
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      setError('An error occurred while updating your profile');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto p-4">
      <div className="bg-amber-50 rounded-lg p-6 max-w-2xl w-full border-2 border-amber-600 shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-serif text-amber-800">Update Your Citizen Profile</h2>
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
        
        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {success}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="personality" className="block text-amber-800 font-medium mb-1">
              Personality Description (2-3 sentences)
            </label>
            <textarea
              id="personality"
              value={personality}
              onChange={(e) => setPersonality(e.target.value)}
              className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 h-24"
              placeholder="Describe your core traits, values, temperament, and notable flaws..."
              required
            />
            <p className="text-xs text-amber-600 mt-1">
              Elaborate on your character's traits, values, and temperament, reflecting experiences and aspirations.
            </p>
          </div>
          
          <div className="mb-4">
            <label className="block text-amber-800 font-medium mb-1">
              Core Personality Traits
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="positiveTrait" className="block text-amber-700 text-sm mb-1">
                  Positive Trait
                </label>
                <input
                  type="text"
                  id="positiveTrait"
                  value={positiveTraitInput}
                  onChange={(e) => setPositiveTraitInput(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                  placeholder="e.g., Meticulous"
                  required
                />
              </div>
              <div>
                <label htmlFor="negativeTrait" className="block text-amber-700 text-sm mb-1">
                  Negative Trait
                </label>
                <input
                  type="text"
                  id="negativeTrait"
                  value={negativeTraitInput}
                  onChange={(e) => setNegativeTraitInput(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                  placeholder="e.g., Calculating"
                  required
                />
              </div>
              <div>
                <label htmlFor="coreMotivation" className="block text-amber-700 text-sm mb-1">
                  Core Motivation
                </label>
                <input
                  type="text"
                  id="coreMotivation"
                  value={coreMotivationInput}
                  onChange={(e) => setCoreMotivationInput(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                  placeholder="e.g., Security-driven"
                  required
                />
              </div>
            </div>
            <p className="text-xs text-amber-600 mt-1">
              These three traits will define your character's core personality.
            </p>
          </div>
          
          <div className="mb-4">
            <label htmlFor="familyMotto" className="block text-amber-800 font-medium mb-1">
              Family Motto
            </label>
            <input
              type="text"
              id="familyMotto"
              value={familyMotto}
              onChange={(e) => setFamilyMotto(e.target.value)}
              className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
              placeholder="A motto that reflects your values and aspirations..."
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="coatOfArms" className="block text-amber-800 font-medium mb-1">
              Coat of Arms Description
            </label>
            <textarea
              id="coatOfArms"
              value={coatOfArms}
              onChange={(e) => setCoatOfArms(e.target.value)}
              className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 h-24"
              placeholder="Describe your coat of arms with symbolic elements representing your profession, values, and family history..."
            />
            <p className="text-xs text-amber-600 mt-1">
              Include symbolic elements appropriate for your social class that represent your profession and values.
            </p>
          </div>
          
          <div className="mb-6">
            <label htmlFor="imagePrompt" className="block text-amber-800 font-medium mb-1">
              Portrait Image Prompt
            </label>
            <textarea
              id="imagePrompt"
              value={imagePrompt}
              onChange={(e) => setImagePrompt(e.target.value)}
              className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 h-24"
              placeholder="Describe how you want your portrait to look, including clothing, setting, and expressions..."
            />
            <p className="text-xs text-amber-600 mt-1">
              Describe a portrait that reflects your social class, profession, and personality traits in Renaissance Venetian style.
            </p>
          </div>
          
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors ${
                isSubmitting ? 'opacity-75 cursor-not-allowed' : ''
              }`}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Updating...' : 'Update Profile'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CitizenProfileUpdater;
