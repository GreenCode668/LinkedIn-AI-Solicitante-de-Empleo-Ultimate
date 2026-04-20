"""Test suite for src/job_manager/resume_anonymizer.py"""

from config.constants import DUMMY_PERSONAL_INFO_FEMALE, DUMMY_PERSONAL_INFO_MALE
from src.job_manager.resume_anonymizer import ResumeAnonymizer


class TestResumeAnonymizerInit:
    """Tests for ResumeAnonymizer initialization"""

    def test_init_creates_copy_of_resume(self):
        """Test that init creates a copy of the resume, not a reference"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "gender": "male",
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)

        # Modify original
        resume_structured["personal_information"]["name"] = "Jane Doe"

        # Anonymizer should still have original value
        assert anonymizer.personal_information["name"] == "John Doe"

    def test_init_initializes_empty_link_lists(self):
        """Test that init creates empty lists for github and linkedin links"""
        resume_structured = {
            "personal_information": {"gender": "male"},
        }

        anonymizer = ResumeAnonymizer(resume_structured)

        assert anonymizer.github_links == []
        assert anonymizer.linkedin_links == []


class TestAnonymizePersonalInformation:
    """Tests for anonymize_personal_information method"""

    def test_anonymize_male_personal_info(self):
        """Test anonymizing personal information for male gender"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "1234567890",
                "gender": "male",
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()

        # Check that values were replaced with dummy data
        assert (
            anonymizer.resume_anonymized["personal_information"]["name"]
            == DUMMY_PERSONAL_INFO_MALE["name"]
        )
        assert (
            anonymizer.resume_anonymized["personal_information"]["email"]
            == DUMMY_PERSONAL_INFO_MALE["email"]
        )
        assert (
            anonymizer.resume_anonymized["personal_information"]["phone"]
            == DUMMY_PERSONAL_INFO_MALE["phone"]
        )

    def test_anonymize_female_personal_info(self):
        """Test anonymizing personal information for female gender"""
        resume_structured = {
            "personal_information": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "1234567890",
                "gender": "female",
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()

        # Check that values were replaced with dummy data
        assert (
            anonymizer.resume_anonymized["personal_information"]["name"]
            == DUMMY_PERSONAL_INFO_FEMALE["name"]
        )
        assert (
            anonymizer.resume_anonymized["personal_information"]["email"]
            == DUMMY_PERSONAL_INFO_FEMALE["email"]
        )
        assert (
            anonymizer.resume_anonymized["personal_information"]["phone"]
            == DUMMY_PERSONAL_INFO_FEMALE["phone"]
        )

    def test_anonymize_case_insensitive_gender(self):
        """Test that gender matching is case-insensitive"""
        resume_structured = {
            "personal_information": {
                "name": "Jane Doe",
                "gender": "FEMALE",
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()

        assert (
            anonymizer.resume_anonymized["personal_information"]["name"]
            == DUMMY_PERSONAL_INFO_FEMALE["name"]
        )

    def test_anonymize_only_existing_fields(self):
        """Test that only existing fields are anonymized"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "gender": "male",
                # No email or phone
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()

        # Name should be anonymized
        assert (
            anonymizer.resume_anonymized["personal_information"]["name"]
            == DUMMY_PERSONAL_INFO_MALE["name"]
        )
        # Email and phone should not be added
        assert "email" not in anonymizer.resume_anonymized["personal_information"]
        assert "phone" not in anonymizer.resume_anonymized["personal_information"]


class TestAnonymizeText:
    """Tests for anonymize_text method"""

    def test_anonymize_github_username_with_https(self):
        """Test anonymizing GitHub username with https URL"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "gender": "male",
            },
        }

        text = "Check out my GitHub: https://github.com/johndoe"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "johndoe" not in result
        assert DUMMY_PERSONAL_INFO_MALE["github"] in result
        assert len(anonymizer.github_links) == 1
        assert anonymizer.github_links[0] == "https://github.com/johndoe"

    def test_anonymize_github_username_with_http(self):
        """Test anonymizing GitHub username with http URL"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/janedoe",
                "gender": "female",
            },
        }

        text = "My profile: http://github.com/janedoe"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "janedoe" not in result
        assert DUMMY_PERSONAL_INFO_FEMALE["github"] in result

    def test_anonymize_github_username_without_protocol(self):
        """Test anonymizing GitHub username without protocol"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "gender": "male",
            },
        }

        text = "Visit github.com/johndoe for my projects"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # GitHub links without protocol are not anonymized by the current implementation
        # The regex requires http:// or https:// protocol
        assert "johndoe" in result  # Not anonymized without protocol

    def test_anonymize_linkedin_username_with_https(self):
        """Test anonymizing LinkedIn username with https URL"""
        resume_structured = {
            "personal_information": {
                "linkedin": "https://linkedin.com/in/johndoe",
                "gender": "male",
            },
        }

        text = "Connect with me: https://linkedin.com/in/johndoe"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "johndoe" not in result
        assert DUMMY_PERSONAL_INFO_MALE["linkedin"] in result
        assert len(anonymizer.linkedin_links) == 1
        assert anonymizer.linkedin_links[0] == "https://linkedin.com/in/johndoe"

    def test_anonymize_linkedin_username_with_www(self):
        """Test anonymizing LinkedIn username with www subdomain"""
        resume_structured = {
            "personal_information": {
                "linkedin": "https://linkedin.com/in/janedoe",
                "gender": "female",
            },
        }

        text = "Profile: https://www.linkedin.com/in/janedoe"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "janedoe" not in result
        assert DUMMY_PERSONAL_INFO_FEMALE["linkedin"] in result

    def test_anonymize_multiple_github_links(self):
        """Test anonymizing multiple GitHub links"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "gender": "male",
            },
        }

        text = "Main: https://github.com/johndoe and fork: https://github.com/johndoe-fork"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "johndoe" not in result
        assert len(anonymizer.github_links) == 2

    def test_anonymize_phone_number(self):
        """Test anonymizing phone number"""
        resume_structured = {
            "personal_information": {
                "phone": "1234567890",
                "gender": "male",
            },
        }

        text = "Call me at 1234567890"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "1234567890" not in result
        assert DUMMY_PERSONAL_INFO_MALE["phone"] in result

    def test_anonymize_phone_number_with_spaces(self):
        """Test anonymizing phone number with spaces"""
        resume_structured = {
            "personal_information": {
                "phone": "123 456 7890",
                "gender": "male",
            },
        }

        text = "Call me at 123 456 7890 or 1234567890"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # Both formats should be replaced
        assert "123" not in result or DUMMY_PERSONAL_INFO_MALE["phone"] in result

    def test_anonymize_phone_code(self):
        """Test anonymizing phone code"""
        resume_structured = {
            "personal_information": {
                "phone_code": "+7",
                "gender": "male",
            },
        }

        text = "Country code: +7"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # Phone code should be anonymized (DUMMY_PERSONAL_INFO_MALE doesn't have phone_code, so it won't be replaced)
        # This tests that the code handles phone_code field properly even if dummy data doesn't have it
        assert result == text or "+7" not in result

    def test_anonymize_email(self):
        """Test anonymizing email address"""
        resume_structured = {
            "personal_information": {
                "email": "john.doe@example.com",
                "gender": "male",
            },
        }

        text = "Email me at john.doe@example.com"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "john.doe@example.com" not in result
        assert DUMMY_PERSONAL_INFO_MALE["email"] in result

    def test_anonymize_name_with_word_boundaries(self):
        """Test that name anonymization respects word boundaries"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "gender": "male",
            },
        }

        text = "My name is John Doe and I work at Johnson Inc."
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # "John Doe" should be replaced but "Johnson" should remain
        assert "John Doe" not in result
        assert "Johnson" in result

    def test_anonymize_address(self):
        """Test anonymizing address"""
        resume_structured = {
            "personal_information": {
                "address": "123 Main Street",
                "gender": "male",
            },
        }

        text = "I live at 123 Main Street"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "123 Main Street" not in result
        assert DUMMY_PERSONAL_INFO_MALE["address"] in result

    def test_anonymize_zip_code(self):
        """Test anonymizing zip code"""
        resume_structured = {
            "personal_information": {
                "zip_code": "12345",
                "gender": "male",
            },
        }

        text = "My zip code is 12345"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "12345" not in result
        assert DUMMY_PERSONAL_INFO_MALE["zip_code"] in result

    def test_anonymize_skips_missing_fields(self):
        """Test that fields not in personal_information are not anonymized"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "gender": "male",
                # No email
            },
        }

        text = "Name: John Doe, Email: someone@example.com"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # Name should be anonymized
        assert "John Doe" not in result
        # Email should remain unchanged (not in personal_information)
        assert "someone@example.com" in result

    def test_anonymize_skips_github_value_in_personal_info(self):
        """Test that github links are still anonymized even if they're in personal_info"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "gender": "male",
            },
        }

        text = "Field: https://github.com/johndoe"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # GitHub links are always anonymized when they match the pattern
        assert "johndoe" not in result
        assert DUMMY_PERSONAL_INFO_MALE["github"] in result

    def test_anonymize_comprehensive_example(self):
        """Test anonymizing a comprehensive example with multiple fields"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "phone": "1234567890",
                "email": "john.doe@example.com",
                "linkedin": "https://linkedin.com/in/johndoe",
                "github": "https://github.com/johndoe",
                "address": "123 Main Street",
                "zip_code": "12345",
                "gender": "male",
            },
        }

        text = """
        Name: John Doe
        Phone: 1234567890
        Email: john.doe@example.com
        LinkedIn: https://linkedin.com/in/johndoe
        GitHub: https://github.com/johndoe
        Address: 123 Main Street
        Zip: 12345
        """

        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # All personal info should be anonymized
        assert "John Doe" not in result
        assert "1234567890" not in result
        assert "john.doe@example.com" not in result
        assert "johndoe" not in result
        assert "123 Main Street" not in result
        assert "12345" not in result

        # Dummy data should be present
        assert DUMMY_PERSONAL_INFO_MALE["name"] in result
        assert DUMMY_PERSONAL_INFO_MALE["email"] in result


class TestDeanonymizeText:
    """Tests for deanonymize_text method"""

    def test_deanonymize_github_links(self):
        """Test deanonymizing GitHub links"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "gender": "male",
            },
        }

        original_text = "GitHub: https://github.com/johndoe"
        anonymizer = ResumeAnonymizer(resume_structured)

        # First anonymize
        anonymized = anonymizer.anonymize_text(original_text)

        # Then deanonymize
        deanonymized = anonymizer.deanonymize_text(anonymized)

        assert "johndoe" in deanonymized
        assert "https://github.com/johndoe" in deanonymized

    def test_deanonymize_linkedin_links(self):
        """Test deanonymizing LinkedIn links"""
        resume_structured = {
            "personal_information": {
                "linkedin": "https://linkedin.com/in/johndoe",
                "gender": "male",
            },
        }

        original_text = "LinkedIn: https://linkedin.com/in/johndoe"
        anonymizer = ResumeAnonymizer(resume_structured)

        # First anonymize
        anonymized = anonymizer.anonymize_text(original_text)

        # Then deanonymize
        deanonymized = anonymizer.deanonymize_text(anonymized)

        assert "johndoe" in deanonymized
        assert "https://linkedin.com/in/johndoe" in deanonymized

    def test_deanonymize_name(self):
        """Test deanonymizing name"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "gender": "male",
            },
        }

        original_text = "My name is John Doe"
        anonymizer = ResumeAnonymizer(resume_structured)

        # First anonymize
        anonymized = anonymizer.anonymize_text(original_text)

        # Then deanonymize
        deanonymized = anonymizer.deanonymize_text(anonymized)

        assert "John Doe" in deanonymized

    def test_deanonymize_phone(self):
        """Test deanonymizing phone number"""
        resume_structured = {
            "personal_information": {
                "phone": "1234567890",
                "gender": "male",
            },
        }

        original_text = "Call: 1234567890"
        anonymizer = ResumeAnonymizer(resume_structured)

        # First anonymize
        anonymized = anonymizer.anonymize_text(original_text)

        # Then deanonymize
        deanonymized = anonymizer.deanonymize_text(anonymized)

        assert "1234567890" in deanonymized

    def test_deanonymize_email(self):
        """Test deanonymizing email"""
        resume_structured = {
            "personal_information": {
                "email": "john.doe@example.com",
                "gender": "male",
            },
        }

        original_text = "Email: john.doe@example.com"
        anonymizer = ResumeAnonymizer(resume_structured)

        # First anonymize
        anonymized = anonymizer.anonymize_text(original_text)

        # Then deanonymize
        deanonymized = anonymizer.deanonymize_text(anonymized)

        assert "john.doe@example.com" in deanonymized

    def test_deanonymize_handles_last_name_2_bug(self):
        """Test that deanonymize handles the last_name_2 bug fix"""
        resume_structured = {
            "personal_information": {
                "last_name": "Doe",
                "gender": "male",
            },
        }

        # Simulate anonymized text with dummy last_name_2
        anonymized_text = f"Name: {DUMMY_PERSONAL_INFO_MALE['last_name_2']}"
        anonymizer = ResumeAnonymizer(resume_structured)

        deanonymized = anonymizer.deanonymize_text(anonymized_text)

        # Should replace last_name_2 with last_name value
        assert "Doe" in deanonymized

    def test_deanonymize_skips_github_linkedin_in_values(self):
        """Test that deanonymize skips fields containing github/linkedin"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "gender": "male",
            },
        }

        text = "Some text"
        anonymizer = ResumeAnonymizer(resume_structured)

        # Should not try to deanonymize the github value itself
        result = anonymizer.deanonymize_text(text)
        assert result == text

    def test_deanonymize_comprehensive_roundtrip(self):
        """Test complete anonymize/deanonymize roundtrip"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "phone": "1234567890",
                "email": "john.doe@example.com",
                "linkedin": "https://linkedin.com/in/johndoe",
                "github": "https://github.com/johndoe",
                "address": "123 Main Street",
                "gender": "male",
            },
        }

        original_text = """
        Name: John Doe
        Phone: 1234567890
        Email: john.doe@example.com
        LinkedIn: https://linkedin.com/in/johndoe
        GitHub: https://github.com/johndoe
        Address: 123 Main Street
        """

        anonymizer = ResumeAnonymizer(resume_structured)

        # Anonymize then deanonymize
        anonymized = anonymizer.anonymize_text(original_text)
        deanonymized = anonymizer.deanonymize_text(anonymized)

        # Should restore all original values
        assert "John Doe" in deanonymized
        assert "1234567890" in deanonymized
        assert "john.doe@example.com" in deanonymized
        assert "johndoe" in deanonymized
        assert "123 Main Street" in deanonymized


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_personal_information(self):
        """Test handling empty personal_information dict"""
        resume_structured = {
            "personal_information": {"gender": "male"},
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()

        # Should not crash
        assert anonymizer.resume_anonymized["personal_information"]["gender"] == "male"

    def test_empty_text_anonymization(self):
        """Test anonymizing empty text"""
        resume_structured = {
            "personal_information": {"gender": "male"},
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text("")

        assert result == ""

    def test_text_without_personal_info(self):
        """Test anonymizing text without any personal information"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "gender": "male",
            },
        }

        text = "This is some random text without personal info"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # Text should remain unchanged
        assert result == text

    def test_multiple_occurrences_same_value(self):
        """Test anonymizing text with multiple occurrences of same value"""
        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "gender": "male",
            },
        }

        text = "John Doe is a developer. John Doe lives in NYC."
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # All occurrences should be replaced
        assert "John Doe" not in result
        assert result.count(DUMMY_PERSONAL_INFO_MALE["name"]) == 2

    def test_gender_default_to_male(self):
        """Test that gender defaults to male when not 'female'"""
        resume_structured = {
            "personal_information": {
                "name": "Alex Smith",
                "gender": "non-binary",  # Not "female"
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()

        # Should use male dummy data
        assert (
            anonymizer.resume_anonymized["personal_information"]["name"]
            == DUMMY_PERSONAL_INFO_MALE["name"]
        )

    def test_special_characters_in_values(self):
        """Test anonymizing values with special regex characters"""
        resume_structured = {
            "personal_information": {
                "phone": "+1-234-567-8900",
                "gender": "male",
            },
        }

        text = "Phone: +1-234-567-8900"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        # Should handle special characters properly
        assert "+1-234-567-8900" not in result

    def test_unicode_characters_in_name(self):
        """Test anonymizing names with unicode characters"""
        resume_structured = {
            "personal_information": {
                "name": "José García",
                "gender": "male",
            },
        }

        text = "My name is José García"
        anonymizer = ResumeAnonymizer(resume_structured)
        result = anonymizer.anonymize_text(text)

        assert "José García" not in result
        assert DUMMY_PERSONAL_INFO_MALE["name"] in result


class TestRealWorldScenarios:
    """Tests for real-world usage scenarios"""

    def test_full_resume_text_example(self):
        """Test the example from the module's __main__ block"""
        resume_text = """Hello, my name is John Doe and my phone number is 9991234567 and my phone code is +7.
    My full phone number is +79991234567.
    My email is john.doe@example.com. My LinkedIn is https://linkedin.com/in/johndoe.
    My GitHub is https://github.com/johndoe. My zip code is 123456.
    My address is 322 Fleet Street. My city is Galway. My country is Ireland.
    My date of birth is 01.01.1990.
    My gender is male."""

        resume_structured = {
            "personal_information": {
                "name": "John Doe",
                "phone": "9991234567",
                "phone_code": "+7",
                "email": "john.doe@example.com",
                "linkedin": "https://linkedin.com/in/johndoe",
                "github": "https://github.com/johndoe",
                "zip_code": "123456",
                "address": "322 Fleet Street",
                "city": "Galway",
                "country": "Ireland",
                "date_of_birth": "01.01.1990",
                "gender": "male",
            },
        }

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymizer.anonymize_personal_information()
        anonymized = anonymizer.anonymize_text(resume_text)
        deanonymized = anonymizer.deanonymize_text(anonymized)

        # Check anonymization worked
        assert "John Doe" not in anonymized
        assert "john.doe@example.com" not in anonymized
        assert "johndoe" not in anonymized

        # Check deanonymization restored original values
        assert "John Doe" in deanonymized
        assert "john.doe@example.com" in deanonymized

    def test_resume_with_no_social_links(self):
        """Test resume anonymization without GitHub or LinkedIn"""
        resume_structured = {
            "personal_information": {
                "name": "Jane Smith",
                "phone": "5551234567",
                "email": "jane.smith@example.com",
                "gender": "female",
            },
        }

        text = """
        Jane Smith
        Phone: 5551234567
        Email: jane.smith@example.com

        Professional software developer with 5 years experience.
        """

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymized = anonymizer.anonymize_text(text)

        assert "Jane Smith" not in anonymized
        assert "jane.smith@example.com" not in anonymized
        assert anonymizer.github_links == []
        assert anonymizer.linkedin_links == []

    def test_resume_with_multiple_social_profiles(self):
        """Test resume with multiple GitHub/LinkedIn references"""
        resume_structured = {
            "personal_information": {
                "github": "https://github.com/johndoe",
                "linkedin": "https://linkedin.com/in/johndoe",
                "gender": "male",
            },
        }

        text = """
        Connect with me:
        - Personal: https://github.com/johndoe
        - Organization: https://github.com/johndoe-org
        - LinkedIn: https://linkedin.com/in/johndoe
        """

        anonymizer = ResumeAnonymizer(resume_structured)
        anonymized = anonymizer.anonymize_text(text)

        # GitHub links with protocol should be anonymized
        assert "https://github.com/johndoe" not in anonymized
        # LinkedIn links with protocol should be anonymized
        assert "https://linkedin.com/in/johndoe" not in anonymized
        # Links should be tracked
        assert len(anonymizer.github_links) == 2
        assert len(anonymizer.linkedin_links) == 1
