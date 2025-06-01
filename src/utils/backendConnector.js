/**
 * Utility functions for communicating with the Python backend
 */

/**
 * Send parsed flight data to the Python backend
 * @param {Object} parsedData - The parsed flight log data
 * @param {String} sessionId - A unique session identifier
 * @returns {Promise} - Response from the backend
 */
export async function sendParsedDataToBackend(parsedData, sessionId = 'default') {
    try {
      console.log(`Sending data to backend with session ID: ${sessionId}`);
      console.log(`Data contains ${Object.keys(parsedData).length} message types`);
      
      const response = await fetch('http://localhost:8000/api/parsed-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          data: parsedData,
          sessionId: sessionId
        }),
      });
      
      const result = await response.json();
      console.log('Backend response:', result);
      return result;
    } catch (error) {
      console.error('Error sending data to backend:', error);
      throw error;
    }
  }