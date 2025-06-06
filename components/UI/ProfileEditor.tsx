import React, { useState, useEffect } from 'react';
import { useWalletContext } from './WalletProvider';

interface ProfileEditorProps {
  onClose: () => void;
  onSuccess?: (updatedProfile: any) => void;
}

const ProfileEditor: React.FC<ProfileEditorProps> = ({ onClose, onSuccess }) => {
  const { citizenProfile } = useWalletContext();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'character'>('basic');
  
  // Basic profile form state
  const [username, setUsername] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [familyMotto, setFamilyMotto] = useState('');
  const [coatOfArmsImageUrl, setCoatOfArmsImageUrl] = useState('');
  
  // Character profile form state
  const [personality, setPersonality] = useState('');
  const [positiveTraitValue, setPositiveTraitValue] = useState('');
  const [negativeTraitValue, setNegativeTraitValue] = useState('');
  const [coreMotivationValue, setCoreMotivationValue] = useState('');
  const [coatOfArmsDescription, setCoatOfArmsDescription] = useState('');
  const [imagePrompt, setImagePrompt] = useState('');
  
  // Initialize form with current citizen data
  useEffect(() => {
    if (citizenProfile) {
      // Basic profile
      setUsername(citizenProfile.username || '');
      setFirstName(citizenProfile.firstName || '');
      setLastName(citizenProfile.lastName || '');
      setFamilyMotto(citizenProfile.familyMotto || '');
      setCoatOfArmsImageUrl(citizenProfile.coatOfArmsImageUrl || '');
      
      // Character profile
      setPersonality(citizenProfile.description || '');
      
      // Try to parse CorePersonality if it exists
      try {
        if (citizenProfile.corePersonality) {
          const corePersonality = typeof citizenProfile.corePersonality === 'string' 
            ? JSON.parse(citizenProfile.corePersonality) 
            : citizenProfile.corePersonality;
          
          if (Array.isArray(corePersonality) && corePersonality.length >= 3) {
            setPositiveTraitValue(corePersonality[0] || '');
            setNegativeTraitValue(corePersonality[1] || '');
            setCoreMotivationValue(corePersonality[2] || '');
          }
        }
      } catch (e) {
        console.error('Error parsing CorePersonality:', e);
      }
      
      setCoatOfArmsDescription(citizenProfile.coatOfArms || '');
      setImagePrompt(citizenProfile.imagePrompt || '');
    }
  }, [citizenProfile]);
  
  const handleBasicProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!citizenProfile || !citizenProfile.id) {
      setError('Citizen profile not found');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const response = await fetch('/api/citizens/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: citizenProfile.id,
          username,
          firstName,
          lastName,
          familyMotto,
          coatOfArmsImageUrl
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Update local storage with the new profile data
        localStorage.setItem('citizenProfile', JSON.stringify(data.citizen));
        
        // Dispatch an event to notify other components about the profile update
        window.dispatchEvent(new CustomEvent('citizenProfileUpdated', { 
          detail: data.citizen 
        }));
        
        // Call the success callback if provided
        if (onSuccess) {
          onSuccess(data.citizen);
        }
        
        // Close the editor
        onClose();
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
  
  const handleCharacterProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!citizenProfile || !citizenProfile.id) {
      setError('Citizen profile not found');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      // Construct the CorePersonality array
      const corePersonality = [
        positiveTraitValue.trim(),
        negativeTraitValue.trim(),
        coreMotivationValue.trim()
      ];
      
      // Validate that all required fields are filled
      if (!personality.trim()) {
        setError('Personality description is required');
        setIsSubmitting(false);
        return;
      }
      
      if (corePersonality.some(trait => !trait)) {
        setError('All three personality traits are required');
        setIsSubmitting(false);
        return;
      }
      
      const response = await fetch('/api/citizens/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: citizenProfile.id,
          description: personality,
          corePersonality: JSON.stringify(corePersonality),
          familyMotto: familyMotto || undefined,
          coatOfArms: coatOfArmsDescription || undefined,
          imagePrompt: imagePrompt || undefined
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Update local storage with the new profile data
        localStorage.setItem('citizenProfile', JSON.stringify(data.citizen));
        
        // Dispatch an event to notify other components about the profile update
        window.dispatchEvent(new CustomEvent('citizenProfileUpdated', { 
          detail: data.citizen 
        }));
        
        // Call the success callback if provided
        if (onSuccess) {
          onSuccess(data.citizen);
        }
        
        // Close the editor
        onClose();
      } else {
        setError(data.error || 'Failed to update character profile');
      }
    } catch (error) {
      console.error('Error updating character profile:', error);
      setError('An error occurred while updating your character profile');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-amber-50 rounded-lg p-6 max-w-2xl w-full border-2 border-amber-600 shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-serif text-amber-800">Edit Profile</h2>
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
        
        {/* Tab Navigation */}
        <div className="flex border-b border-amber-300 mb-4">
          <button
            className={`py-2 px-4 font-medium ${
              activeTab === 'basic' 
                ? 'text-amber-800 border-b-2 border-amber-600' 
                : 'text-amber-600 hover:text-amber-700'
            }`}
            onClick={() => setActiveTab('basic')}
          >
            Basic Profile
          </button>
          <button
            className={`py-2 px-4 font-medium ${
              activeTab === 'character' 
                ? 'text-amber-800 border-b-2 border-amber-600' 
                : 'text-amber-600 hover:text-amber-700'
            }`}
            onClick={() => setActiveTab('character')}
          >
            Character Profile
          </button>
        </div>
        
        {/* Basic Profile Tab */}
        {activeTab === 'basic' && (
          <form onSubmit={handleBasicProfileSubmit}>
            <div className="mb-4">
              <label htmlFor="username" className="block text-amber-800 font-medium mb-1">
                Username
              </label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                placeholder="Your public username"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label htmlFor="firstName" className="block text-amber-800 font-medium mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                  placeholder="First name"
                />
              </div>
              <div>
                <label htmlFor="lastName" className="block text-amber-800 font-medium mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  id="lastName"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                  placeholder="Last name"
                />
              </div>
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
                placeholder="Your family motto"
              />
            </div>
            
            <div className="mb-6">
              <label htmlFor="coatOfArmsImageUrl" className="block text-amber-800 font-medium mb-1">
                Coat of Arms Image URL
              </label>
              <input
                type="text"
                id="coatOfArmsImageUrl"
                value={coatOfArmsImageUrl}
                onChange={(e) => setCoatOfArmsImageUrl(e.target.value)}
                className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                placeholder="https://example.com/your-image.jpg"
              />
              <p className="text-xs text-amber-600 mt-1">
                Enter a URL to an image for your coat of arms
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
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        )}
        
        {/* Character Profile Tab */}
        {activeTab === 'character' && (
          <form onSubmit={handleCharacterProfileSubmit}>
            <div className="mb-4">
              <label htmlFor="personality" className="block text-amber-800 font-medium mb-1">
                Personality Description (2-3 sentences)
              </label>
              <textarea
                id="personality"
                value={personality}
                onChange={(e) => setPersonality(e.target.value)}
                className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 h-24"
                placeholder="Describe your character's core traits, values, temperament, and notable flaws..."
              />
            </div>
            
            <div className="mb-4">
              <label className="block text-amber-800 font-medium mb-1">
                Core Personality Traits
              </label>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label htmlFor="positiveTrait" className="block text-xs text-amber-700 mb-1">
                    Positive Trait
                  </label>
                  <input
                    type="text"
                    id="positiveTrait"
                    value={positiveTraitValue}
                    onChange={(e) => setPositiveTraitValue(e.target.value)}
                    className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Shrewd"
                  />
                </div>
                <div>
                  <label htmlFor="negativeTrait" className="block text-xs text-amber-700 mb-1">
                    Negative Trait
                  </label>
                  <input
                    type="text"
                    id="negativeTrait"
                    value={negativeTraitValue}
                    onChange={(e) => setNegativeTraitValue(e.target.value)}
                    className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Overambitious"
                  />
                </div>
                <div>
                  <label htmlFor="coreMotivation" className="block text-xs text-amber-700 mb-1">
                    Core Motivation
                  </label>
                  <input
                    type="text"
                    id="coreMotivation"
                    value={coreMotivationValue}
                    onChange={(e) => setCoreMotivationValue(e.target.value)}
                    className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Legacy-driven"
                  />
                </div>
              </div>
            </div>
            
            <div className="mb-4">
              <label htmlFor="coatOfArmsDescription" className="block text-amber-800 font-medium mb-1">
                Coat of Arms Description
              </label>
              <textarea
                id="coatOfArmsDescription"
                value={coatOfArmsDescription}
                onChange={(e) => setCoatOfArmsDescription(e.target.value)}
                className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 h-24"
                placeholder="Describe your coat of arms with symbolic elements representing your profession, values, and family history..."
              />
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
                placeholder="Detailed description for generating your character portrait..."
              />
              <p className="text-xs text-amber-600 mt-1">
                This prompt will be used to generate your character's portrait image
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
                {isSubmitting ? 'Saving...' : 'Save Character Profile'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default ProfileEditor;
