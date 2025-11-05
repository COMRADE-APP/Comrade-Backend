from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet
from Events.serializers import EventSerializer
from Events.models import Event, EventRegistration, EventCategory, EventType, EventLocation, EventSponsor, EventSpeaker, EventFeedback, EventSchedule, EventResource, EventAttendee, EventOrganizer, EventSession, EventTicket, EventVenue, EventPromotion, EventMedia, EventPartner, EventVolunteer, EventAgenda, EventLogistics, EventBudget, EventReport, EventSurvey, EventReminder, EventCheckIn, EventCheckOut, EventNotification, EventPoll, EventDiscussion, EventWorkshop, EventWebinar, EventConference, EventFestival, EventExhibition, EventFair, EventMeetup, EventSummit, EventSymposium, EventForum, EventPanel, EventDebate, EventNetworking, EventAwards, EventCeremony, EventGala, EventReception, EventBanquet, EventDinner, EventLunch, EventBreakfast, EventBrunch, EventPicnic, EventParty, EventCelebration, EventParade, EventMarch, EventProtest, EventRally, EventDemonstration, EventSitIn, EventStrike, EventBoycott, EventVigil, EventMemorial, EventTribute, EventCommemoration, EventAnniversary, EventBirthday, EventWedding, EventEngagement, EventGraduation, EventRetirement, EventFarewell, EventWelcome, EventOpening, EventClosing, EventLaunch, EventInauguration, EventDedication, EventBlessing, EventCeremonyType, EventCeremonyLocation, EventCeremonyDate, EventCeremonyTime, EventCeremonyDuration, EventCeremonyHost, EventCeremonyGuest, EventCeremonySpeaker, EventCeremonySponsor, EventCeremonyOrganizer, EventCeremonyAttendee, EventCeremonyMedia, EventCeremonyPromotion, EventCeremonyResource, EventCeremonySchedule, EventCeremonyFeedback, EventCeremonySurvey, EventCeremonyReport
# Create your views here.
