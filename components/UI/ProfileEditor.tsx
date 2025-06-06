import React, { useState, useEffect } from 'react';
import { useWalletContext } from './WalletProvider';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ProfileEditorProps {
  onClose: () => void;
  onSuccess?: (updatedProfile: any) => void;
}

const ProfileEditor: React.FC<ProfileEditorProps> = ({ onClose, onSuccess }) => {
  const { citizenProfile } = useWalletContext();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'advanced'>('basic');
  
  // Form state
  const [username, setUsername] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [familyMotto, setFamilyMotto] = useState('');
  const [coatOfArmsImageUrl, setCoatOfArmsImageUrl] = useState('');
  const [personality, setPersonality] = useState('');
  const [corePersonality, setCorePersonality] = useState<string[]>(['', '', '']);
  const [coatOfArms, setCoatOfArms] = useState('');
  const [imagePrompt, setImagePrompt] = useState('');
  
  // Helper function to update a specific index in the corePersonality array
  const updateCorePersonality = (index: number, value: string) => {
    const newArray = [...corePersonality];
    newArray[index] = value;
    setCorePersonality(newArray);
  };
  
  // Initialize form with current citizen data
  useEffect(() => {
    if (citizenProfile) {
      setUsername(citizenProfile.username || '');
      setFirstName(citizenProfile.firstName || '');
      setLastName(citizenProfile.lastName || '');
      setFamilyMotto(citizenProfile.familyMotto || '');
      setCoatOfArmsImageUrl(citizenProfile.coatOfArmsImageUrl || '');
      setPersonality(citizenProfile.description || '');
      
      // Parse CorePersonality if it exists
      if (citizenProfile.corePersonality && Array.isArray(citizenProfile.corePersonality) && citizenProfile.corePersonality.length === 3) {
        setCorePersonality(citizenProfile.corePersonality);
      } else if (typeof citizenProfile.corePersonality === 'string') {
        try {
          const parsed = JSON.parse(citizenProfile.corePersonality);
          if (Array.isArray(parsed) && parsed.length === 3) {
            setCorePersonality(parsed);
          }
        } catch (e) {
          console.error('Error parsing CorePersonality:', e);
        }
      }
      
      setCoatOfArms(citizenProfile.coatOfArms || '');
      setImagePrompt(citizenProfile.imagePrompt || '');
    }
  }, [citizenProfile]);
  
  const handleSubmit = async (e: React.FormEvent) => {
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
          coatOfArmsImageUrl,
          description: personality,
          corePersonality,
          coatOfArms,
          imagePrompt
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
  
  const handleGenerateAI = async () => {
    if (!citizenProfile || !citizenProfile.username) {
      setError('Citizen profile not found');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const response = await fetch('/api/citizens/generate-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: citizenProfile.username
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Update form fields with AI-generated content
        if (data.profile) {
          setPersonality(data.profile.Personality || personality);
          if (data.profile.CorePersonality && Array.isArray(data.profile.CorePersonality) && data.profile.CorePersonality.length === 3) {
            setCorePersonality(data.profile.CorePersonality);
          }
          setFamilyMotto(data.profile.familyMotto || familyMotto);
          setCoatOfArms(data.profile.coatOfArms || coatOfArms);
          setImagePrompt(data.profile.imagePrompt || imagePrompt);
        }
      } else {
        setError(data.error || 'Failed to generate profile');
      }
    } catch (error) {
      console.error('Error generating profile:', error);
      setError('An error occurred while generating your profile');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-amber-50 rounded-lg p-6 max-w-4xl w-full border-2 border-amber-600 shadow-xl max-h-[90vh] overflow-y-auto">
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
        
        {/* Tabs */}
        <div className="flex border-b border-amber-300 mb-4">
          <button
            className={`px-4 py-2 font-medium ${
              activeTab === 'basic' 
                ? 'bg-amber-100 text-amber-900 border-t-2 border-l-2 border-r-2 border-amber-300 rounded-t-md' 
                : 'text-amber-700 hover:text-amber-900'
            }`}
            onClick={() => setActiveTab('basic')}
            type="button"
          >
            Basic Information
          </button>
          <button
            className={`px-4 py-2 font-medium ${
              activeTab === 'advanced' 
                ? 'bg-amber-100 text-amber-900 border-t-2 border-l-2 border-r-2 border-amber-300 rounded-t-md' 
                : 'text-amber-700 hover:text-amber-900'
            }`}
            onClick={() => setActiveTab('advanced')}
            type="button"
          >
            Character Details
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          {activeTab === 'basic' && (
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
          )}
          
          {activeTab === 'advanced' && (
            <>
              <div className="mb-4">
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="personality" className="block text-amber-800 font-medium">
                    Personality Description
                  </label>
                  <button
                    type="button"
                    onClick={handleGenerateAI}
                    className="text-xs bg-amber-600 text-white px-2 py-1 rounded hover:bg-amber-700 transition-colors"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Generating...' : 'Generate with AI'}
                  </button>
                </div>
                <textarea
                  id="personality"
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 min-h-[100px]"
                  placeholder="2-3 sentences describing your core traits, values, temperament, and notable flaws"
                />
                <p className="text-xs text-amber-600 mt-1">
                  Describe your character's personality in 2-3 sentences
                </p>
              </div>
              
              <div className="mb-4">
                <label className="block text-amber-800 font-medium mb-1">
                  Core Personality Traits
                </label>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label htmlFor="positiveTraitInput" className="block text-xs text-amber-700 mb-1">
                      Positive Trait
                    </label>
                    <input
                      type="text"
                      id="positiveTraitInput"
                      value={corePersonality[0]}
                      onChange={(e) => updateCorePersonality(0, e.target.value)}
                      className="w-full p-2 border border-green-300 bg-green-50 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                      placeholder="e.g., Observant"
                    />
                  </div>
                  <div>
                    <label htmlFor="negativeTraitInput" className="block text-xs text-amber-700 mb-1">
                      Negative Trait
                    </label>
                    <input
                      type="text"
                      id="negativeTraitInput"
                      value={corePersonality[1]}
                      onChange={(e) => updateCorePersonality(1, e.target.value)}
                      className="w-full p-2 border border-red-300 bg-red-50 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                      placeholder="e.g., Suspicious"
                    />
                  </div>
                  <div>
                    <label htmlFor="motivationInput" className="block text-xs text-amber-700 mb-1">
                      Core Motivation
                    </label>
                    <input
                      type="text"
                      id="motivationInput"
                      value={corePersonality[2]}
                      onChange={(e) => updateCorePersonality(2, e.target.value)}
                      className="w-full p-2 border border-blue-300 bg-blue-50 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Security-driven"
                    />
                  </div>
                </div>
                <p className="text-xs text-amber-600 mt-1">
                  Each trait should be a single word or very short phrase
                </p>
              </div>
              
              <div className="mb-4">
                <label htmlFor="coatOfArms" className="block text-amber-800 font-medium mb-1">
                  Coat of Arms Description
                </label>
                <textarea
                  id="coatOfArms"
                  value={coatOfArms}
                  onChange={(e) => setCoatOfArms(e.target.value)}
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 min-h-[80px]"
                  placeholder="Describe your coat of arms following heraldic conventions of Renaissance Venice"
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
                  className="w-full p-2 border border-amber-300 rounded focus:outline-none focus:ring-2 focus:ring-amber-500 min-h-[100px]"
                  placeholder="Detailed description for generating your character portrait"
                />
                <p className="text-xs text-amber-600 mt-1">
                  This prompt will be used to generate your character portrait
                </p>
              </div>
              
              {/* Preview section */}
              {(personality || corePersonality.some(trait => trait) || coatOfArms || imagePrompt) && (
                <div className="mb-6 p-4 bg-amber-100 rounded-lg border border-amber-300">
                  <h3 className="text-lg font-serif text-amber-800 mb-2">Preview</h3>
                  
                  {personality && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-amber-700">Personality:</h4>
                      <ReactMarkdown 
                        className="text-sm text-amber-800 italic"
                        remarkPlugins={[remarkGfm]}
                      >
                        {personality}
                      </ReactMarkdown>
                    </div>
                  )}
                  
                  {corePersonality.some(trait => trait) && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-amber-700">Core Traits:</h4>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {corePersonality[0] && (
                          <span className="px-2 py-1 text-xs font-medium text-green-800 bg-green-100 rounded-full">
                            {corePersonality[0]}
                          </span>
                        )}
                        {corePersonality[1] && (
                          <span className="px-2 py-1 text-xs font-medium text-red-800 bg-red-100 rounded-full">
                            {corePersonality[1]}
                          </span>
                        )}
                        {corePersonality[2] && (
                          <span className="px-2 py-1 text-xs font-medium text-blue-800 bg-blue-100 rounded-full">
                            {corePersonality[2]}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {familyMotto && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-amber-700">Family Motto:</h4>
                      <p className="text-sm text-amber-800 italic">"{familyMotto}"</p>
                    </div>
                  )}
                  
                  {coatOfArms && (
                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-amber-700">Coat of Arms:</h4>
                      <p className="text-sm text-amber-800">{coatOfArms}</p>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
          
          <div className="flex justify-between space-x-3">
            <div>
              {activeTab === 'advanced' && (
                <button
                  type="button"
                  onClick={() => setActiveTab('basic')}
                  className="px-4 py-2 bg-amber-200 text-amber-800 rounded hover:bg-amber-300 transition-colors"
                  disabled={isSubmitting}
                >
                  Back to Basic Info
                </button>
              )}
              {activeTab === 'basic' && (
                <button
                  type="button"
                  onClick={() => setActiveTab('advanced')}
                  className="px-4 py-2 bg-amber-200 text-amber-800 rounded hover:bg-amber-300 transition-colors"
                  disabled={isSubmitting}
                >
                  Continue to Character Details
                </button>
              )}
            </div>
            <div className="flex space-x-3">
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
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileEditor;
