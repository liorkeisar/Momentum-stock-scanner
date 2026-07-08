"""
joke_generator.py
Random Joke Generator using Official Joke API
"""

import requests
import json
from typing import Dict, Optional


class JokeGenerator:
    """
    A class to generate random jokes using the Official Joke API
    API: https://official-joke-api.appspot.com/
    """
    
    BASE_URL = "https://official-joke-api.appspot.com"
    
    def __init__(self):
        """Initialize the JokeGenerator"""
        self.base_url = self.BASE_URL
        self.timeout = 5  # 5 seconds timeout
    
    def get_random_joke(self) -> Optional[Dict]:
        """
        Fetch a random joke from the API
        
        Returns:
            dict: A dictionary containing the joke with keys:
                - 'id': Joke ID
                - 'type': Type of joke (general, knock-knock, programming)
                - 'setup': The setup of the joke
                - 'punchline': The punchline
            None: If the request fails
        """
        try:
            endpoint = f"{self.base_url}/random_joke"
            response = requests.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            print("Error: Request timed out")
            return None
        
        except requests.exceptions.ConnectionError:
            print("Error: Failed to connect to the API")
            return None
        
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code}")
            return None
        
        except Exception as e:
            print(f"Error fetching joke: {e}")
            return None
    
    def get_random_jokes_by_count(self, count: int = 3) -> Optional[list]:
        """
        Fetch multiple random jokes
        
        Args:
            count (int): Number of jokes to fetch (1-10 recommended)
        
        Returns:
            list: List of joke dictionaries
            None: If the request fails
        """
        if count < 1:
            print("Error: Count must be at least 1")
            return None
        
        try:
            endpoint = f"{self.base_url}/jokes/random/{count}"
            response = requests.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            print("Error: Request timed out")
            return None
        
        except requests.exceptions.ConnectionError:
            print("Error: Failed to connect to the API")
            return None
        
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code}")
            return None
        
        except Exception as e:
            print(f"Error fetching jokes: {e}")
            return None
    
    def get_joke_by_type(self, joke_type: str = "general") -> Optional[Dict]:
        """
        Fetch a random joke by type
        
        Args:
            joke_type (str): Type of joke (general, knock-knock, programming)
        
        Returns:
            dict: A joke dictionary
            None: If the request fails
        """
        valid_types = ["general", "knock-knock", "programming"]
        
        if joke_type not in valid_types:
            print(f"Error: Invalid joke type. Choose from: {', '.join(valid_types)}")
            return None
        
        try:
            endpoint = f"{self.base_url}/jokes/{joke_type}/random"
            response = requests.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            print("Error: Request timed out")
            return None
        
        except requests.exceptions.ConnectionError:
            print("Error: Failed to connect to the API")
            return None
        
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code}")
            return None
        
        except Exception as e:
            print(f"Error fetching joke: {e}")
            return None
    
    def format_joke(self, joke: Dict) -> str:
        """
        Format a joke for display
        
        Args:
            joke (dict): A joke dictionary
        
        Returns:
            str: Formatted joke string
        """
        if not joke:
            return "No joke available"
        
        setup = joke.get("setup", "")
        punchline = joke.get("punchline", "")
        joke_type = joke.get("type", "").upper()
        
        formatted = f"\n{'='*50}\n"
        formatted += f"[{joke_type}]\n"
        formatted += f"{setup}\n"
        formatted += f"→ {punchline}\n"
        formatted += f"{'='*50}\n"
        
        return formatted
    
    def display_joke(self, joke: Optional[Dict]) -> None:
        """
        Display a joke in a formatted way
        
        Args:
            joke (dict): A joke dictionary
        """
        if joke:
            print(self.format_joke(joke))
        else:
            print("Failed to load joke. Please try again later.")
    
    def display_multiple_jokes(self, jokes: Optional[list]) -> None:
        """
        Display multiple jokes
        
        Args:
            jokes (list): List of joke dictionaries
        """
        if not jokes:
            print("Failed to load jokes. Please try again later.")
            return
        
        for i, joke in enumerate(jokes, 1):
            print(f"\nJoke #{i}")
            print(self.format_joke(joke))


def main():
    """Main function to demonstrate the JokeGenerator"""
    
    generator = JokeGenerator()
    
    print("🎭 Welcome to the Random Joke Generator! 🎭")
    print("\nOptions:")
    print("1. Get a random joke")
    print("2. Get multiple random jokes")
    print("3. Get a joke by type (general, knock-knock, programming)")
    print("4. Exit")
    
    while True:
        choice = input("\nChoose an option (1-4): ").strip()
        
        if choice == "1":
            print("\n📝 Fetching a random joke...")
            joke = generator.get_random_joke()
            generator.display_joke(joke)
        
        elif choice == "2":
            try:
                count = int(input("How many jokes do you want? (1-10): "))
                print(f"\n📝 Fetching {count} jokes...")
                jokes = generator.get_random_jokes_by_count(count)
                generator.display_multiple_jokes(jokes)
            except ValueError:
                print("Error: Please enter a valid number")
        
        elif choice == "3":
            print("\nJoke types: general, knock-knock, programming")
            joke_type = input("Enter joke type: ").strip().lower()
            print(f"\n📝 Fetching a {joke_type} joke...")
            joke = generator.get_joke_by_type(joke_type)
            generator.display_joke(joke)
        
        elif choice == "4":
            print("\n😄 Thanks for using the Joke Generator! Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
